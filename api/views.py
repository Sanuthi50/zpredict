from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from .models import AdminUpload, User, ChatHistory, PredictionSession, SavedPrediction
from .tasks import process_pdf_and_create_vectorstore
import os
from .models import Feedback
from .serializers import FeedbackSerializer
from django.conf import settings
from langchain.chains import RetrievalQA
from langchain_huggingface import HuggingFacePipeline
from transformers import pipeline, AutoTokenizer
import torch
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework import status
import re
from rest_framework.decorators import api_view, parser_classes, permission_classes
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage
from django.conf import settings 
from functools import lru_cache
import google.generativeai as genai
import threading
from .ml_utils import ml_predictor_instance
from .careermodel_utils import career_predictor_instance, recommend_careers_logic
from rest_framework import generics, permissions
from django.shortcuts import get_object_or_404
from django.db.models import Q

# Configure Gemini once globally
genai.configure(api_key=settings.GEMINI_API_KEY)

# Cache embeddings model to avoid reloading
_model_cache = {}
_cache_lock = threading.Lock()

def clean_text(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

def get_cached_embeddings():
    with _cache_lock:
        if 'embeddings' not in _model_cache:
            print("Loading embeddings model (first time)...")
            _model_cache['embeddings'] = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cuda' if torch.cuda.is_available() else 'cpu'}
            )
            print("Embeddings model loaded!")
        return _model_cache['embeddings']

def get_cached_llm():
    """Get cached LLM pipeline or create new one"""
    with _cache_lock:
        if 'llm' not in _model_cache:
            print("Loading LLM model (first time)...")
            model_name = "google/flan-t5-base"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            device = 0 if torch.cuda.is_available() else -1
            hf_pipeline = pipeline(
                "text2text-generation",
                model=model_name,
                tokenizer=tokenizer,
                max_length=512,
                device=device,
            )
            _model_cache['llm'] = HuggingFacePipeline(pipeline=hf_pipeline)
            print("LLM model loaded!")
        return _model_cache['llm']

def get_cached_vectorstore(vectorstore_path):
    """Get cached vectorstore or load from path"""
    with _cache_lock:
        cache_key = f'vectorstore_{vectorstore_path}'
        if cache_key not in _model_cache:
            print(f"Loading vectorstore from {vectorstore_path} (first time)...")
            embeddings = get_cached_embeddings()
            _model_cache[cache_key] = FAISS.load_local(
                vectorstore_path, embeddings, allow_dangerous_deserialization=True
            )
            print("Vectorstore loaded!")
        return _model_cache[cache_key]

def warmup_models():
    """Warmup models on server start (optional)"""
    try:
        print("Warming up AI models...")
        get_cached_embeddings()
        get_cached_llm()
        print("Models warmed up successfully!")
    except Exception as e:
        print(f"Model warmup failed: {e}")
        print("Models will be loaded on first request instead.")

@method_decorator(csrf_exempt, name='dispatch')
class ReprocessPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (request.user.is_admin or request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Only admins can reprocess PDFs"}, status=403)

        try:
            # Get the latest active upload
            upload = AdminUpload.objects.filter(active=True).latest('uploaded_at')
            
            # Reset processing status
            upload.processing_status = 'pending'
            upload.save()
            
            # Start the processing task with automatic fallback
            from .utils import ensure_pdf_processing
            ensure_pdf_processing(upload.id)
            
            return Response({"message": "PDF reprocessing started"})
            
        except AdminUpload.DoesNotExist:
            return Response({"error": "No active uploads found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class AdminVerifyView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.is_admin or request.user.is_staff or request.user.is_superuser:
            return Response({"isAdmin": True})
        return Response({"error": "Not an admin user"}, status=403)

class AdminUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Check if user is admin
        if not (request.user.is_admin or request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Admin access required"}, status=403)

        file = request.FILES.get('pdf_file')
        description = request.data.get('description', '')
        
        if not file:
            return Response({"error": "Please upload a PDF file."}, status=400)
            
        if not file.name.lower().endswith('.pdf'):
            return Response({"error": "Only PDF files are allowed."}, status=400)

        # Check file size (optional - set your own limits)
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 100 * 1024 * 1024)  # 100MB default
        if file.size > max_size:
            return Response({
                "error": f"File too large. Maximum size is {max_size // (1024*1024)}MB"
            }, status=400)

        try:
            # Create upload record
            upload = AdminUpload.objects.create(
                admin=request.user,
                pdf_file=file,
                original_filename=file.name,
                file_size=file.size,
                description=description,
                processing_status='pending'
            )

            # Start background processing with automatic fallback
            from .utils import ensure_pdf_processing
            ensure_pdf_processing(upload.id)

            return Response({
                "message": "Upload successful, processing in background.",
                "upload_id": upload.id,
                "filename": upload.original_filename,
                "file_size": upload.get_file_size_display()
            })

        except Exception as e:
            return Response({
                "error": f"Upload failed: {str(e)}"
            }, status=500)

    def get(self, request):
        """Get list of uploads for admin"""
        if not (request.user.is_admin or request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Admin access required"}, status=403)

        uploads = AdminUpload.objects.filter(admin=request.user, active=True)
        upload_data = []
        
        for upload in uploads:
            upload_data.append({
                'id': upload.id,
                'filename': upload.original_filename,
                'file_size': upload.get_file_size_display(),
                'uploaded_at': upload.uploaded_at,
                'processing_status': upload.processing_status,
                'description': upload.description,
                'is_active': upload.active
            })
        
        return Response({'uploads': upload_data})

class AdminDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not (request.user.is_admin or request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Admin access required"}, status=403)
        
        # Get dashboard statistics
        stats = {
            'total_students': User.objects.filter(user_type='student', active=True).count(),
            'total_uploads': AdminUpload.objects.filter(admin=request.user, active=True).count(),
            'total_chats': ChatHistory.objects.filter(active=True).count(),
            'total_predictions': PredictionSession.objects.filter(active=True).count(),
            'total_saved_predictions': SavedPrediction.objects.filter(active=True).count(),
            'pending_uploads': AdminUpload.objects.filter(
                admin=request.user, 
                processing_status='pending'
            ).count(),
        }
        
        # Get recent uploads
        recent_uploads = AdminUpload.objects.filter(
            admin=request.user, 
            active=True
        )[:5]
        
        uploads_data = [{
            'id': upload.id,
            'filename': upload.original_filename,
            'uploaded_at': upload.uploaded_at,
            'processing_status': upload.processing_status,
            'file_size': upload.get_file_size_display()
        } for upload in recent_uploads]
        
        # Get recent prediction sessions
        recent_predictions = PredictionSession.objects.filter(active=True)[:5]
        predictions_data = [{
            'id': session.id,
            'student': f"{session.student.first_name} {session.student.last_name}",
            'stream': session.stream,
            'z_score': session.z_score,
            'predicted_at': session.predicted_at,
            'total_predictions_generated': session.total_predictions_generated
        } for session in recent_predictions]
        
        return Response({
            'stats': stats,
            'recent_uploads': uploads_data,
            'recent_predictions': predictions_data
        })
@method_decorator(csrf_exempt, name='dispatch')
class ChatAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check student permissions
        if not request.user.is_student:
            return Response({"error": "Only students can access chat."}, status=403)
        if not request.user.active:
            return Response({"error": "Student account is not active."}, status=403)

        question = request.data.get('question')
        if not question:
            return Response({"error": "Question is required."}, status=400)

        try:
            # Process synchronously for now (instead of Celery)
            answer = self._process_question(request.user, question)
            return Response({"answer": answer})

        except Exception as e:
            return Response({"error": f"Chat failed: {str(e)}"}, status=500)

    def _process_question(self, user, question):
        """Process question synchronously"""
        try:
            import google.generativeai as genai
            from django.conf import settings
            
            # Configure Gemini
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            context = ""
            source = "UGC Handbook"

            # Check for active handbook vectorstore
            active_upload = AdminUpload.objects.filter(
                active=True, 
                processing_status='completed'
            ).first()
            
            if active_upload and active_upload.vectorstore_path:
                try:
                    # Use cached embeddings and vectorstore
                    embeddings = get_cached_embeddings()
                    vectorstore = FAISS.load_local(
                        active_upload.vectorstore_path, 
                        embeddings, 
                        allow_dangerous_deserialization=True
                    )
                    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
                    results = retriever.get_relevant_documents(question)

                    if results:
                        context = "\n\n".join([doc.page_content for doc in results])
                        # Prevent overloading Gemini
                        context = context[:5000]
                except Exception as e:
                    print(f"Vectorstore error: {e}")
                    context = ""

            # Generate response with Gemini
            model = genai.GenerativeModel("gemini-1.5-flash")
            if context:
                prompt = f"Context (UGC Handbook):\n{context}\n\nQuestion: {question}"
            else:
                prompt = f"Answer this question using reliable online sources:\n\n{question}"
                source = "Gemini Online"

            response = model.generate_content(prompt)
            answer = response.text if response else "No response from Gemini."

            # Save chat history
            ChatHistory.objects.create(
                student=user, 
                question=question, 
                answer=answer
            )

            return answer

        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "exceeded" in error_msg:
                return "Free tier limit reached. Please try again tomorrow."
            return f"Chat error: {e}"
class ChatResultAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        from celery.result import AsyncResult
        result = AsyncResult(task_id)
        if result.state == "PENDING":
            return Response({"status": "pending"})
        elif result.state == "SUCCESS":
            return Response({"status": "completed", "answer": result.result})
        elif result.state == "FAILURE":
            return Response({"status": "failed", "error": str(result.result)})

@method_decorator(csrf_exempt, name='dispatch')
class PredictionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_student:
            return Response({"error": "Only students can access predictions."}, status=403)

        data = request.data
        year = data.get('year')
        z_score = data.get('z_score')
        stream = data.get('stream')
        district = data.get('district')

        if not all([year, z_score, stream, district]):
            return Response({"error": "Year, Z-score, stream, and district are required."}, status=400)

        try:
            z_score = float(z_score)
            year = int(year)
        except (ValueError, TypeError):
            return Response({"error": "Invalid year or Z-score format."}, status=400)

        if not ml_predictor_instance or not ml_predictor_instance.models_loaded:
            return Response({"error": "Prediction models are not available."}, status=500)

        try:
            # Get available courses/universities for the stream
            course_university_pairs = ml_predictor_instance.get_available_courses_for_stream(stream, limit=20)

            predictions = []
            for pair in course_university_pairs:
                course = pair['course_name']
                university = pair['university_name']

                # Predict cutoff
                cutoff = ml_predictor_instance.predict_cutoff(
                    year=year,
                    university=university,
                    course_name=course,
                    district=district,
                    stream=stream,
                    aptitude_test=False,      # or extract from DB/UGC data if you have it
                    all_island_merit=True     # same here
                )

                # Predict probability
                prob = ml_predictor_instance.predict_selection_probability(
                    z_score=z_score,
                    stream=stream,
                    district=district,
                    course_name=course,
                    university=university,
                    aptitude_test=False,
                    all_island_merit=True
                )

                predictions.append({
                    "university_name": university,
                    "course_name": course,
                    "predicted_cutoff": round(cutoff, 3),
                    "predicted_probability": round(prob, 3),
                    "recommendation": ml_predictor_instance.get_recommendation_status(prob)
                })

            # Sort by probability
            predictions.sort(key=lambda x: x['predicted_probability'], reverse=True)

            return Response({
                "predictions": predictions,
                "total_predictions": len(predictions),
                "message": "Predictions generated successfully!"
            })

        except Exception as e:
            return Response({"error": f"Prediction failed: {str(e)}"}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class SavePredictionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Save a specific prediction for a student"""
        if not request.user.is_student:
            return Response({"error": "Only students can save predictions."}, status=403)

        data = request.data
        session_id = data.get('session_id')
        university_name = data.get('university_name')
        course_name = data.get('course_name')
        predicted_cutoff = data.get('predicted_cutoff')
        predicted_probability = data.get('predicted_probability')
        aptitude_test_required = data.get('aptitude_test_required', False)
        all_island_merit = data.get('all_island_merit', True)
        rank_in_results = data.get('rank', 0)
        notes = data.get('notes', '')

        # Validate required fields
        if not all([session_id, university_name, course_name, predicted_cutoff is not None, predicted_probability is not None]):
            return Response({
                "error": "Session ID, university name, course name, cutoff, and probability are required."
            }, status=400)

        try:
            # Get the prediction session
            session = PredictionSession.objects.get(id=session_id, student=request.user)
            
            # Check if already saved
            existing = SavedPrediction.objects.filter(
                student=request.user,
                session=session,
                university_name=university_name,
                course_name=course_name
            ).first()
            
            if existing:
                return Response({
                    "error": "This prediction is already saved."
                }, status=400)

            # Create saved prediction
            saved_prediction = SavedPrediction.objects.create(
                student=request.user,
                session=session,
                university_name=university_name,
                course_name=course_name,
                predicted_cutoff=float(predicted_cutoff),
                predicted_probability=float(predicted_probability),
                aptitude_test_required=bool(aptitude_test_required),
                all_island_merit=bool(all_island_merit),
                rank_in_results=int(rank_in_results),
                notes=notes
            )

            return Response({
                "message": "Prediction saved successfully!",
                "saved_prediction_id": saved_prediction.id
            })

        except PredictionSession.DoesNotExist:
            return Response({"error": "Prediction session not found."}, status=404)
        except Exception as e:
            return Response({
                "error": f"Failed to save prediction: {str(e)}"
            }, status=500)

    def get(self, request):
        """Get saved predictions for a student"""
        if not request.user.is_student:
            return Response({"error": "Only students can view saved predictions."}, status=403)

        saved_predictions = SavedPrediction.objects.filter(
            student=request.user, 
            active=True
        ).select_related('session')

        predictions_data = []
        for prediction in saved_predictions:
            predictions_data.append({
                'id': prediction.id,
                'university_name': prediction.university_name,
                'course_name': prediction.course_name,
                'predicted_cutoff': prediction.predicted_cutoff,
                'predicted_probability': prediction.predicted_probability,
                'probability_percentage': prediction.probability_percentage,
                'selection_likely': prediction.selection_likely,
                'aptitude_test_required': prediction.aptitude_test_required,
                'all_island_merit': prediction.all_island_merit,
                'rank_in_results': prediction.rank_in_results,
                'notes': prediction.notes,
                'saved_at': prediction.saved_at,
                'session': {
                    'id': prediction.session.id,
                    'year': prediction.session.year,
                    'z_score': prediction.session.z_score,
                    'stream': prediction.session.stream,
                    'district': prediction.session.district,
                    'predicted_at': prediction.session.predicted_at
                }
            })

        return Response({'saved_predictions': predictions_data})

    def delete(self, request, prediction_id):
        """Delete a saved prediction"""
        if not request.user.is_student:
            return Response({"error": "Only students can delete saved predictions."}, status=403)

        try:
            saved_prediction = SavedPrediction.objects.get(
                id=prediction_id, 
                student=request.user
            )
            saved_prediction.delete()
            
            return Response({"message": "Saved prediction deleted successfully!"})
        
        except SavedPrediction.DoesNotExist:
            return Response({"error": "Saved prediction not found."}, status=404)

@method_decorator(csrf_exempt, name='dispatch')
class PredictionHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get prediction history for a student"""
        if not request.user.is_student:
            return Response({"error": "Only students can view prediction history."}, status=403)

        sessions = PredictionSession.objects.filter(
            student=request.user, 
            active=True
        ).prefetch_related('saved_predictions')

        history_data = []
        for session in sessions:
            saved_count = session.saved_predictions.filter(active=True).count()
            
            history_data.append({
                'id': session.id,
                'year': session.year,
                'z_score': session.z_score,
                'stream': session.stream,
                'district': session.district,
                'total_predictions_generated': session.total_predictions_generated,
                'saved_predictions_count': saved_count,
                'confidence_level': session.confidence_level,
                'predicted_at': session.predicted_at
            })

        return Response({'prediction_history': history_data})

@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    """Admin login endpoint"""
    username = request.data.get('email')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({
            'detail': 'Username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Authenticate admin user
    user = authenticate(username=username, password=password)
    
    if user and user.is_admin:
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'admin_id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        })
    else:
        return Response({
            'detail': 'Invalid admin credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([AllowAny])
def admin_register(request):
    """Register new admin"""
    data = request.data
    
    required_fields = ['email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if field not in data or not data[field]:
            return Response({
                'detail': f'{field} is required'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if email exists
    if User.objects.filter(email=data['email']).exists():
        return Response({
            'detail': 'Email already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        admin = User.objects.create_user(
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            user_type='admin',
            is_staff=True
        )
        
        return Response({
            'detail': 'Admin registered successfully!',
            'admin_id': admin.id
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'detail': f'Registration failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_student(request):
    data = request.data
    
    # Validate required fields
    required_fields = ['first_name', 'last_name', 'email', 'password']
    for field in required_fields:
        if field not in data or not data[field]:
            return Response({
                'detail': f'{field} is required'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if email already exists
    if User.objects.filter(email=data['email']).exists():
        return Response({
            'detail': 'Email already exists'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Create student user
        student = User.objects.create_user(
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            user_type='student'
        )
        
        return Response({
            'detail': 'Student registered successfully!',
            'student_id': student.id
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'detail': f'Registration failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_student(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({
            'detail': 'Email and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Authenticate using email as username
    user = authenticate(request, username=email, password=password)

    if user is not None and user.is_active and user.is_student:
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'student_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email
        })
    else:
        return Response({
            'detail': 'Invalid credentials or account not active'
        }, status=status.HTTP_401_UNAUTHORIZED)

@method_decorator(csrf_exempt, name='dispatch')
class ModelStatusAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get status of AI models and upload processing"""
        try:
            from .utils import check_celery_worker_health
            from .models import AdminUpload
            
            # Check if models are loaded
            models_status = {
                'embeddings_loaded': 'embeddings' in _model_cache,
                'llm_loaded': 'llm' in _model_cache,
                'vectorstore_count': len([k for k in _model_cache.keys() if k.startswith('vectorstore_')]),
                'cache_size': len(_model_cache)
            }
            
            # Check upload processing status
            upload_status = {
                'celery_worker_healthy': check_celery_worker_health(),
                'pending_uploads': AdminUpload.objects.filter(processing_status='pending').count(),
                'processing_uploads': AdminUpload.objects.filter(processing_status='processing').count(),
                'completed_uploads': AdminUpload.objects.filter(processing_status='completed').count(),
                'failed_uploads': AdminUpload.objects.filter(processing_status='failed').count()
            }
            
            return Response({
                'status': 'healthy',
                'models': models_status,
                'uploads': upload_status,
                'message': 'System status retrieved successfully'
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'error': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RecommendationView(APIView):

    """API endpoint for career recommendations."""

    def post(self, request, *args, **kwargs):
        """Handles POST requests for career recommendations."""
        degree_program = request.data.get('degree_program')

        if not degree_program:
            return Response({"error": "Please provide a 'degree_program' in the request data."}, status=400)

        if not career_predictor_instance or not career_predictor_instance.models_loaded:
            return Response({"error": "Career prediction models are not available."}, status=500)

        try:
            raw_recommendations = recommend_careers_logic(
                degree_program,
                career_predictor_instance.hybrid_df,
                None,  # occupation_tfidf_matrix is calculated within the function
                career_predictor_instance.tfidf_vectorizer,
                career_predictor_instance.occupation_df
            )

            # Transform the data to match frontend expectations
            recommendations = []
            for rec in raw_recommendations:
                transformed_rec = {
                    "title": rec.get('ONET_Title', rec.get('Title', 'Unknown Career')),
                    "similarity_score": rec.get('Similarity_Score_Degree', 0),
                    "vacancies": rec.get('Number_of_Vacancies', 0),
                    "combined_score": rec.get('Combined_Score', 0),
                    "occupation": rec.get('Sri_Lankan_Occupation', None),
                    "skills": rec.get('Skills', []),
                    "abilities": rec.get('Abilities', [])
                }
                recommendations.append(transformed_rec)

            return Response({
                "recommendations": recommendations,
                "total_recommendations": len(recommendations),
                "message": "Career recommendations generated successfully!"
            })

        except Exception as e:
            return Response({"error": f"Career recommendation failed: {str(e)}"}, status=500)

    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get career insights for a student"""
        if not request.user.is_student:
            return Response({"error": "Only students can access career insights."}, status=403)
        
        # Placeholder implementation
        return Response({
            "message": "Career insights feature coming soon!",
            "insights": []
        })

# =============================
# Feedback Management Views
# =============================

@method_decorator(csrf_exempt, name='dispatch')
class FeedbackListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all active feedbacks (students can see all, admins can see all)"""
        if request.user.is_admin or request.user.is_staff or request.user.is_superuser:
            # Admin can see all feedbacks
            feedbacks = Feedback.objects.filter(active=True).select_related('student')
        else:
            # Students can see all feedbacks
            feedbacks = Feedback.objects.filter(active=True).select_related('student')
        
        feedback_data = []
        for feedback in feedbacks:
            feedback_data.append({
                'id': feedback.id,
                'student_name': f"{feedback.student.first_name} {feedback.student.last_name}",
                'student_email': feedback.student.email,
                'feedback': feedback.feedback,
                'rating': feedback.rating,
                'rating_display': feedback.get_rating_display() if feedback.rating else None,
                'submitted_at': feedback.submitted_at,
                'is_own_feedback': feedback.student == request.user
            })
        
        return Response({'feedbacks': feedback_data})
    
    def post(self, request):
        """Create new feedback (only students)"""
        if not request.user.is_student:
            return Response({"error": "Only students can submit feedback."}, status=403)
        
        feedback_text = request.data.get('feedback')
        rating = request.data.get('rating')
        
        if not feedback_text:
            return Response({"error": "Feedback text is required."}, status=400)
        
        try:
            feedback = Feedback.objects.create(
                student=request.user,
                feedback=feedback_text,
                rating=rating
            )
            
            return Response({
                "message": "Feedback submitted successfully!",
                "feedback_id": feedback.id
            })
            
        except Exception as e:
            return Response({
                "error": f"Failed to submit feedback: {str(e)}"
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class FeedbackDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, feedback_id):
        """Get specific feedback details"""
        try:
            feedback = Feedback.objects.get(id=feedback_id, active=True)
            
            # Check permissions
            if not (request.user.is_admin or request.user.is_staff or request.user.is_superuser or feedback.student == request.user):
                return Response({"error": "You don't have permission to view this feedback."}, status=403)
            
            feedback_data = {
                'id': feedback.id,
                'student_name': f"{feedback.student.first_name} {feedback.student.last_name}",
                'student_email': feedback.student.email,
                'feedback': feedback.feedback,
                'rating': feedback.rating,
                'rating_display': feedback.get_rating_display() if feedback.rating else None,
                'submitted_at': feedback.submitted_at,
                'is_own_feedback': feedback.student == request.user
            }
            
            return Response({'feedback': feedback_data})
            
        except Feedback.DoesNotExist:
            return Response({"error": "Feedback not found."}, status=404)
    
    def put(self, request, feedback_id):
        """Update feedback (only owner or admin)"""
        try:
            feedback = Feedback.objects.get(id=feedback_id, active=True)
            
            # Check permissions
            if not (request.user.is_admin or request.user.is_staff or request.user.is_superuser or feedback.student == request.user):
                return Response({"error": "You don't have permission to update this feedback."}, status=403)
            
            feedback_text = request.data.get('feedback')
            rating = request.data.get('rating')
            
            if feedback_text is not None:
                feedback.feedback = feedback_text
            if rating is not None:
                feedback.rating = rating
            
            feedback.save()
            
            return Response({
                "message": "Feedback updated successfully!",
                "feedback_id": feedback.id
            })
            
        except Feedback.DoesNotExist:
            return Response({"error": "Feedback not found."}, status=404)
        except Exception as e:
            return Response({
                "error": f"Failed to update feedback: {str(e)}"
            }, status=500)
    
    def delete(self, request, feedback_id):
        """Soft delete feedback (only owner or admin)"""
        try:
            feedback = Feedback.objects.get(id=feedback_id, active=True)
            
            # Check permissions
            if not (request.user.is_admin or request.user.is_staff or request.user.is_superuser or feedback.student == request.user):
                return Response({"error": "You don't have permission to delete this feedback."}, status=403)
            
            # Soft delete
            feedback.active = False
            feedback.save()
            
            return Response({"message": "Feedback deleted successfully!"})
            
        except Feedback.DoesNotExist:
            return Response({"error": "Feedback not found."}, status=404)
        except Exception as e:
            return Response({
                "error": f"Failed to delete feedback: {str(e)}"
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class UserFeedbackView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user's feedbacks"""
        if not request.user.is_student:
            return Response({"error": "Only students can view their feedbacks."}, status=403)
        
        feedbacks = Feedback.objects.filter(student=request.user, active=True)
        
        feedback_data = []
        for feedback in feedbacks:
            feedback_data.append({
                'id': feedback.id,
                'feedback': feedback.feedback,
                'rating': feedback.rating,
                'rating_display': feedback.get_rating_display() if feedback.rating else None,
                'submitted_at': feedback.submitted_at
            })
        
        return Response({'user_feedbacks': feedback_data})

# =============================
# Student Dashboard Views
# =============================

@method_decorator(csrf_exempt, name='dispatch')
class StudentDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get student dashboard data"""
        if not request.user.is_student:
            return Response({"error": "Only students can access dashboard."}, status=403)
        
        # Get user info
        user_data = {
            'id': request.user.id,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'date_joined': request.user.date_joined,
            'is_active': request.user.active
        }
        
        # Get prediction statistics
        total_sessions = PredictionSession.objects.filter(student=request.user, active=True).count()
        total_saved_predictions = SavedPrediction.objects.filter(student=request.user, active=True).count()
        total_chats = ChatHistory.objects.filter(student=request.user, active=True).count()
        total_feedbacks = Feedback.objects.filter(student=request.user, active=True).count()
        
        # Get recent prediction sessions
        recent_sessions = PredictionSession.objects.filter(
            student=request.user, 
            active=True
        ).order_by('-predicted_at')[:5]
        
        sessions_data = []
        for session in recent_sessions:
            sessions_data.append({
                'id': session.id,
                'year': session.year,
                'z_score': session.z_score,
                'stream': session.stream,
                'district': session.district,
                'total_predictions_generated': session.total_predictions_generated,
                'confidence_level': session.confidence_level,
                'predicted_at': session.predicted_at
            })
        
        # Get recent saved predictions
        recent_saved = SavedPrediction.objects.filter(
            student=request.user, 
            active=True
        ).select_related('session').order_by('-saved_at')[:5]
        
        saved_data = []
        for prediction in recent_saved:
            saved_data.append({
                'id': prediction.id,
                'university_name': prediction.university_name,
                'course_name': prediction.course_name,
                'predicted_cutoff': prediction.predicted_cutoff,
                'predicted_probability': prediction.predicted_probability,
                'probability_percentage': prediction.probability_percentage,
                'selection_likely': prediction.selection_likely,
                'saved_at': prediction.saved_at,
                'session': {
                    'id': prediction.session.id,
                    'year': prediction.session.year,
                    'z_score': prediction.session.z_score,
                    'stream': prediction.session.stream
                }
            })
        
        return Response({
            'user': user_data,
            'statistics': {
                'total_sessions': total_sessions,
                'total_saved_predictions': total_saved_predictions,
                'total_chats': total_chats,
                'total_feedbacks': total_feedbacks
            },
            'recent_sessions': sessions_data,
            'recent_saved_predictions': saved_data
        })

@method_decorator(csrf_exempt, name='dispatch')
class StudentProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get student profile"""
        if not request.user.is_student:
            return Response({"error": "Only students can access profile."}, status=403)
        
        profile_data = {
            'id': request.user.id,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'date_joined': request.user.date_joined,
            'is_active': request.user.active
        }
        
        return Response({'profile': profile_data})
    
    def put(self, request):
        """Update student profile"""
        if not request.user.is_student:
            return Response({"error": "Only students can update profile."}, status=403)
        
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        email = request.data.get('email')
        
        # Validate email uniqueness if changed
        if email and email != request.user.email:
            if User.objects.filter(email=email).exists():
                return Response({"error": "Email already exists."}, status=400)
        
        try:
            if first_name is not None:
                request.user.first_name = first_name
            if last_name is not None:
                request.user.last_name = last_name
            if email is not None:
                request.user.email = email
            
            request.user.save()
            
            return Response({
                "message": "Profile updated successfully!",
                "profile": {
                    'id': request.user.id,
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                    'email': request.user.email,
                    'date_joined': request.user.date_joined,
                    'is_active': request.user.active
                }
            })
            
        except Exception as e:
            return Response({
                "error": f"Failed to update profile: {str(e)}"
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class StudentDeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        """Soft delete student account"""
        if not request.user.is_student:
            return Response({"error": "Only students can delete their account."}, status=403)
        
        try:
            # Soft delete the user
            request.user.active = False
            request.user.save()
            
            return Response({"message": "Account deleted successfully!"})
            
        except Exception as e:
            return Response({
                "error": f"Failed to delete account: {str(e)}"
            }, status=500)

# =============================
# Admin Feedback Management
# =============================

@method_decorator(csrf_exempt, name='dispatch')
class AdminFeedbackManagementView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all feedbacks for admin management"""
        if not (request.user.is_admin or request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Admin access required."}, status=403)
        
        # Get all feedbacks with student info
        feedbacks = Feedback.objects.filter(active=True).select_related('student')
        
        feedback_data = []
        for feedback in feedbacks:
            feedback_data.append({
                'id': feedback.id,
                'student_id': feedback.student.id,
                'student_name': f"{feedback.student.first_name} {feedback.student.last_name}",
                'student_email': feedback.student.email,
                'feedback': feedback.feedback,
                'rating': feedback.rating,
                'rating_display': feedback.get_rating_display() if feedback.rating else None,
                'submitted_at': feedback.submitted_at
            })
        
        return Response({'feedbacks': feedback_data})
    
    def delete(self, request, feedback_id):
        """Admin delete feedback"""
        if not (request.user.is_admin or request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Admin access required."}, status=403)
        
        try:
            feedback = Feedback.objects.get(id=feedback_id, active=True)
            
            # Soft delete
            feedback.active = False
            feedback.save()
            
            return Response({"message": "Feedback deleted successfully!"})
            
        except Feedback.DoesNotExist:
            return Response({"error": "Feedback not found."}, status=404)
        except Exception as e:
            return Response({
                "error": f"Failed to delete feedback: {str(e)}"
            }, status=500)

# =============================
# Enhanced Admin Dashboard
# =============================

@method_decorator(csrf_exempt, name='dispatch')
class EnhancedAdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get enhanced admin dashboard with feedback statistics"""
        if not (request.user.is_admin or request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Admin access required."}, status=403)
        
        # Get dashboard statistics
        stats = {
            'total_students': User.objects.filter(user_type='student', active=True).count(),
            'total_admins': User.objects.filter(user_type='admin', active=True).count(),
            'total_uploads': AdminUpload.objects.filter(admin=request.user, active=True).count(),
            'total_chats': ChatHistory.objects.filter(active=True).count(),
            'total_predictions': PredictionSession.objects.filter(active=True).count(),
            'total_saved_predictions': SavedPrediction.objects.filter(active=True).count(),
            'total_feedbacks': Feedback.objects.filter(active=True).count(),
            'pending_uploads': AdminUpload.objects.filter(
                admin=request.user, 
                processing_status='pending'
            ).count(),
        }
        
        # Get recent feedbacks
        recent_feedbacks = Feedback.objects.filter(active=True).select_related('student')[:5]
        feedbacks_data = [{
            'id': feedback.id,
            'student_name': f"{feedback.student.first_name} {feedback.student.last_name}",
            'student_email': feedback.student.email,
            'feedback': feedback.feedback[:100] + "..." if len(feedback.feedback) > 100 else feedback.feedback,
            'rating': feedback.rating,
            'rating_display': feedback.get_rating_display() if feedback.rating else None,
            'submitted_at': feedback.submitted_at
        } for feedback in recent_feedbacks]
        
        # Get recent uploads
        recent_uploads = AdminUpload.objects.filter(
            admin=request.user, 
            active=True
        )[:5]
        
        uploads_data = [{
            'id': upload.id,
            'filename': upload.original_filename,
            'uploaded_at': upload.uploaded_at,
            'processing_status': upload.processing_status,
            'file_size': upload.get_file_size_display()
        } for upload in recent_uploads]
        
        # Get recent prediction sessions
        recent_predictions = PredictionSession.objects.filter(active=True)[:5]
        predictions_data = [{
            'id': session.id,
            'student': f"{session.student.first_name} {session.student.last_name}",
            'stream': session.stream,
            'z_score': session.z_score,
            'predicted_at': session.predicted_at,
            'total_predictions_generated': session.total_predictions_generated
        } for session in recent_predictions]
        
        return Response({
            'stats': stats,
            'recent_feedbacks': feedbacks_data,
            'recent_uploads': uploads_data,
            'recent_predictions': predictions_data
        })