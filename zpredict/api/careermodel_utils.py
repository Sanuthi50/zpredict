import os
import joblib
import pandas as pd
import numpy as np
import string
from django.conf import settings
from django.core.cache import cache
import logging
from typing import Dict, List, Any, Optional, Tuple
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class CareerPredictor:
    def __init__(self):
        self.hybrid_df = None
        self.occupation_df = None
        self.tfidf_vectorizer = None
        self.model_path = os.path.join(settings.BASE_DIR, 'api','careermodel')
        self.models_loaded = False
        self._loading_lock = False  # Simple flag to prevent concurrent loading
        
        # Don't load models immediately - use lazy loading instead
        logger.info(f"CareerPredictor initialized with lazy loading. Models will be loaded on first use.")
    
    def load_models(self) -> None:
        """Load trained models and encoders with improved error handling"""
        try:
            # Check if models are cached
            cached_models = cache.get('ml_models')
            if cached_models:
                self.hybrid_df = cached_models.get('hybrid_df')
                self.occupation_df = cached_models.get('occupation_df')
                self.tfidf_vectorizer = cached_models.get('tfidf_vectorizer')
                
                # Only use cache if all models are actually loaded
                if self.hybrid_df is not None and self.occupation_df is not None and self.tfidf_vectorizer is not None:
                    self.models_loaded = True
                    logger.info("Models loaded from cache")
                    return
                else:
                    logger.warning("Cached models are invalid, clearing cache and loading fresh")
                    cache.delete('ml_models')
            
            # Create model directory if it doesn't exist
            if not os.path.exists(self.model_path):
                logger.error(f"Model directory does not exist: {self.model_path}")
                return
            
            # Load all models
            self._load_hybrid_df()
            self._load_occupation_df()
            self._load_tfidf_vectorizer()
            
            # Cache models for 1 hour if at least one model was loaded
            if self.hybrid_df is not None or self.occupation_df is not None:
                cache.set('ml_models', {
                    'hybrid_df': self.hybrid_df,
                    'occupation_df': self.occupation_df,
                    'tfidf_vectorizer': self.tfidf_vectorizer,
                }, 3600)
                self.models_loaded = True
                logger.info("Models loaded and cached successfully")
            else:
                logger.warning("No models were loaded successfully")
                self.models_loaded = False
            
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            self.models_loaded = False
    
    def _load_hybrid_df(self) -> None:
        """Load hybrid_df model"""
        hybrid_df_path = os.path.join(self.model_path, 'hybrid_df.pkl')
        if os.path.exists(hybrid_df_path):
            try:
                self.hybrid_df = joblib.load(hybrid_df_path)
                logger.info("hybrid_df model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading hybrid_df: {str(e)}")
                self.hybrid_df = None
    def _load_occupation_df(self) -> None:
        """Load occupation_df model"""
        occupation_df_path = os.path.join(self.model_path, 'occupation_df.pkl')
        if os.path.exists(occupation_df_path):
            try:
                self.occupation_df = joblib.load(occupation_df_path)
                logger.info("occupation_df loaded successfully")
            except Exception as e:
                logger.error(f"Error loading occupation_df: {str(e)}")
                self.occupation_df = None
    def _load_tfidf_vectorizer(self) -> None:
        """Load tfidf vectorizer model"""
        tfidf_vectorizer_path = os.path.join(self.model_path, 'tfidf_vectorizer.pkl')
        if os.path.exists(tfidf_vectorizer_path):
            try:
                self.tfidf_vectorizer = joblib.load(tfidf_vectorizer_path)
                logger.info("tfidf_vectorizer model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading tfidf_vectorizer: {str(e)}")
                self.tfidf_vectorizer = None
    def _ensure_models_loaded(self) -> bool:
        """Ensure models are loaded using lazy loading pattern"""
        if self.models_loaded:
            return True
            
        # Prevent concurrent loading attempts
        if self._loading_lock:
            logger.info("Career models are currently being loaded by another thread, waiting...")
            import time
            for _ in range(30):  # Wait up to 3 seconds
                time.sleep(0.1)
                if self.models_loaded:
                    return True
            logger.warning("Timeout waiting for career models to load")
            return False
            
        try:
            self._loading_lock = True
            logger.info("Loading career models on-demand...")
            self.load_models()
            
            if self.models_loaded:
                logger.info("Career models loaded successfully via lazy loading")
            else:
                logger.error("Failed to load career models")
            return self.models_loaded
            
        finally:
            self._loading_lock = False
    
    def _validate_models_loaded(self) -> bool:
        """Check if models are properly loaded"""
        return self._ensure_models_loaded()

def recommend_careers_logic(degree_program, hybrid_df, occupation_tfidf_matrix, tfidf_vectorizer, occupation_df, N=30, weight_similarity=0.6, weight_vacancies=0.4):
    """
    Recommends careers based on a student's degree or program, considering
    similarity to O*NET occupations and Sri Lankan vacancy numbers.

    Args:
        degree_program (str): The student's degree or program.
        hybrid_df (pd.DataFrame): The hybrid dataset containing linked
                                   occupations, vacancies, skills, and abilities.
        occupation_tfidf_matrix (sparse matrix): The TF-IDF matrix of O*NET occupations.
        tfidf_vectorizer (TfidfVectorizer): The fitted TF-IDF vectorizer.
        occupation_df (pd.DataFrame): The original O*NET occupation DataFrame.
        N (int): The number of top similar O*NET occupations to consider for re-ranking.
        weight_similarity (float): The weight given to the similarity score in the combined score.
        weight_vacancies (float): The weight given to the normalized vacancy numbers in the combined score.


    Returns:
        list: A list of recommended careers with their details and combined scores.
    """
    if hybrid_df is None or occupation_df is None or tfidf_vectorizer is None:
        logger.error("Model components not loaded. Cannot provide recommendations.")
        return []

    # Ensure 'combined_text' exists in occupation_df for TF-IDF transformation
    if 'combined_text' not in occupation_df.columns:
        occupation_df['combined_text'] = occupation_df['Title'] + ' ' + occupation_df['Description']


    # Preprocess the input degree/program text
    cleaned_degree_program = degree_program.lower()
    cleaned_degree_program = cleaned_degree_program.translate(str.maketrans('', '', string.punctuation))

    # Transform the preprocessed degree/program text into a TF-IDF vector
    try:
        degree_program_tfidf = tfidf_vectorizer.transform([cleaned_degree_program])
    except ValueError as e:
        print(f"Error transforming degree program text: {e}")
        return []


    # Calculate the cosine similarity
    # Need to recreate occupation_tfidf_matrix as it wasn't saved
    occupation_tfidf_matrix = tfidf_vectorizer.transform(occupation_df['combined_text'])
    cosine_sim_degree = cosine_similarity(degree_program_tfidf, occupation_tfidf_matrix).flatten()

    # Get the similarity scores and sort the O*NET occupations
    sim_scores_degree = list(enumerate(cosine_sim_degree))
    sim_scores_degree = sorted(sim_scores_degree, key=lambda x: x[1], reverse=True)

    # Select the top N most similar O*NET occupations
    top_N_indices = [x[0] for x in sim_scores_degree[0:N]]
    top_N_onet_occupations = occupation_df.iloc[top_N_indices].copy()
    top_N_onet_occupations['Similarity_Score_Degree'] = [sim_scores_degree[i][1] for i in range(N)]

    # Find corresponding entries in the hybrid_df and implement re-ranking
    recommended_careers = []
    # Get all unique ONET_SOC_Codes from the top N ONET occupations
    top_n_onet_soc_codes = top_N_onet_occupations['O*NET-SOC Code'].tolist()

    # Filter hybrid_df to only include entries for the top N ONET SOC codes
    filtered_hybrid_df = hybrid_df[hybrid_df['ONET_SOC_Code'].isin(top_n_onet_soc_codes)].copy()


    if not filtered_hybrid_df.empty:
        # Normalize vacancy numbers for better scaling in the combined score
        max_vacancies = filtered_hybrid_df['Number_of_Vacancies'].max()
        if max_vacancies > 0:
             filtered_hybrid_df['Normalized_Vacancies'] = filtered_hybrid_df['Number_of_Vacancies'] / max_vacancies
        else:
             filtered_hybrid_df['Normalized_Vacancies'] = 0


        # Merge with top_N_onet_occupations to get the degree similarity score for re-ranking
        re_ranking_df = pd.merge(
            filtered_hybrid_df,
            top_N_onet_occupations[['O*NET-SOC Code', 'Similarity_Score_Degree']],
            left_on='ONET_SOC_Code',
            right_on='O*NET-SOC Code',
            how='inner'
        )

        # Calculate combined score - considering the similarity from degree to ONET
        # and the normalized vacancies from the hybrid link
        re_ranking_df['Combined_Score'] = (weight_similarity * re_ranking_df['Similarity_Score_Degree']) + (weight_vacancies * re_ranking_df['Normalized_Vacancies'])


        # Sort by combined score
        recommended_careers = re_ranking_df.sort_values(by='Combined_Score', ascending=False).to_dict('records')


    # Return the top recommendations (e.g., top 10)
    return recommended_careers[:10]

# Global variable to hold the lazy-loaded career predictor instance
career_predictor_instance = None

def get_career_predictor():
    """Get career predictor instance using lazy loading pattern"""
    global career_predictor_instance
    if career_predictor_instance is None:
        try:
            logger.info("Creating Career Predictor instance with lazy loading...")
            career_predictor_instance = CareerPredictor()
            logger.info("Career Predictor instance created successfully")
        except Exception as e:
            logger.error(f"Failed to create Career Predictor instance: {str(e)}")
            career_predictor_instance = None
    return career_predictor_instance