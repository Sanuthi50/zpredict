# Core Django and DRF imports
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)

# DRF imports
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, parser_classes, permission_classes, action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken

# Third-party imports
from django_filters.rest_framework import DjangoFilterBackend
from functools import lru_cache
import google.generativeai as genai
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFacePipeline
import os
import re
import threading
import torch
from transformers import pipeline, AutoTokenizer

# Local imports
from .careermodel_utils import get_career_predictor, recommend_careers_logic
from .ml_utils import get_ml_predictor
from .models import AdminUpload, User, ChatHistory, PredictionSession, SavedPrediction, Feedback, CareerSession, SavedCareerPrediction
from .serializers import (
    FeedbackSerializer, UserSerializer, StudentSerializer, AdminSerializer, 
    UserProfileSerializer, PredictionSessionSerializer, PredictionSessionCreateSerializer,
    SavedPredictionSerializer, SavedPredictionCreateSerializer, AdminUploadSerializer, 
    AdminUploadCreateSerializer, ChatHistorySerializer, ChatHistoryCreateSerializer,
    FeedbackCreateSerializer, CareerSessionSerializer, 
    CareerSessionCreateSerializer, SavedCareerPredictionSerializer, SavedCareerPredictionCreateSerializer
)
from .tasks import process_pdf_and_create_vectorstore

# Configure Gemini once globally with error handling
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    logger.info("Gemini API configured successfully")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    # Continue without Gemini - the app will work with local models only

# Cache embeddings model to avoid reloading
_model_cache = {}
_cache_lock = threading.Lock()

def clean_text(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

def is_admin_user(user):
    """Helper function to check if user has admin privileges"""
    return user.is_admin or user.is_staff or user.is_superuser

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
        if not is_admin_user(request.user):
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
        if is_admin_user(request.user):
            return Response({"isAdmin": True})
        return Response({"error": "Not an admin user"}, status=403)

class AdminUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Check if user is admin
        if not is_admin_user(request.user):
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
        """Get list of uploads for admin with pagination"""
        if not is_admin_user(request.user):
            return Response({"error": "Admin access required"}, status=403)

        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        search = request.GET.get('search', '')
        
        # Build query
        uploads_query = AdminUpload.objects.filter(
            admin=request.user, 
            active=True
        ).order_by('-uploaded_at')
        
        # Apply search filter if provided
        if search:
            uploads_query = uploads_query.filter(
                Q(original_filename__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # Calculate pagination
        total_uploads = uploads_query.count()
        total_pages = (total_uploads + per_page - 1) // per_page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        
        uploads = uploads_query[start_index:end_index]
        
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
        
        # Pagination info
        pagination = {
            'current_page': page,
            'total_pages': total_pages,
            'total_items': total_uploads,
            'per_page': per_page,
            'has_next': page < total_pages,
            'has_previous': page > 1
        }
        
        return Response({
            'uploads': upload_data,
            'pagination': pagination
        })

class AdminDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not is_admin_user(request.user):
            return Response({"error": "Admin access required"}, status=403)
        
        # Get dashboard statistics
        stats = {
            'total_students': User.objects.filter(user_type='student', active=True).count(),
            'total_admins': User.objects.filter(user_type='admin', active=True).count(),
            'total_uploads': AdminUpload.objects.filter(admin=request.user, active=True).count(),
            'total_chats': ChatHistory.objects.filter(active=True).count(),
            'total_predictions': PredictionSession.objects.filter(active=True).count(),
            'total_saved_predictions': SavedPrediction.objects.filter(active=True).count(),
            'total_career_sessions': CareerSession.objects.filter(active=True).count(),
            'total_saved_career_predictions': SavedCareerPrediction.objects.count(),
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
        
        # Get recent uploads with pagination support
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        search = request.GET.get('search', '')
        
        uploads_query = AdminUpload.objects.filter(
            admin=request.user, 
            active=True
        ).order_by('-uploaded_at')
        
        # Apply search filter if provided
        if search:
            uploads_query = uploads_query.filter(
                Q(original_filename__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # Calculate pagination
        total_uploads = uploads_query.count()
        total_pages = (total_uploads + per_page - 1) // per_page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        
        recent_uploads = uploads_query[start_index:end_index]
        
        uploads_data = [{
            'id': upload.id,
            'filename': upload.original_filename,
            'uploaded_at': upload.uploaded_at,
            'processing_status': upload.processing_status,
            'file_size': upload.get_file_size_display(),
            'description': upload.description or ''
        } for upload in recent_uploads]
        
        # Pagination info
        pagination = {
            'current_page': page,
            'total_pages': total_pages,
            'total_items': total_uploads,
            'per_page': per_page,
            'has_next': page < total_pages,
            'has_previous': page > 1
        }
        
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
            'recent_predictions': predictions_data,
            'pagination': pagination
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
            try:
                model = genai.GenerativeModel("gemini-1.5-flash")
                if context:
                    prompt = f"Context (UGC Handbook):\n{context}\n\nQuestion: {question}"
                else:
                    prompt = f"Answer this question using reliable online sources:\n\n{question}"
                    source = "Gemini Online"

                response = model.generate_content(prompt)
                answer = response.text if response else "No response from Gemini."
            except Exception as e:
                error_msg = str(e)
                if "10054" in error_msg or "forcibly closed" in error_msg.lower():
                    logger.warning(f"Gemini API network error: {error_msg}")
                    answer = "I'm experiencing network connectivity issues. Please try again in a moment."
                else:
                    logger.error(f"Gemini API error: {error_msg}")
                    answer = "I'm unable to process your request at the moment. Please try again later."

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
        aptitude_test = data.get('aptitude_test', False)
        all_island_merit = data.get('all_island_merit', True)

        if not all([year, z_score, stream, district]):
            return Response({"error": "Year, Z-score, stream, and district are required."}, status=400)

        try:
            z_score = float(z_score)
            year = int(year)
        except (ValueError, TypeError):
            return Response({"error": "Invalid year or Z-score format."}, status=400)

        try:
            ml_predictor = get_ml_predictor()
            if not ml_predictor:
                logger.error("Failed to get ML predictor instance")
                return Response({"error": "Failed to initialize prediction service."}, status=500)
                
            if not ml_predictor._ensure_models_loaded():
                logger.error("Failed to load ML models")
                # Get model status for debugging
                model_status = {
                    'regressor_loaded': bool(ml_predictor.regressor),
                    'classifier_loaded': bool(ml_predictor.classifier),
                    'classifier_encoder_loaded': bool(ml_predictor.classifier_encoder),
                    'feature_encoder_loaded': bool(ml_predictor.feature_encoder),
                    'valid_courses_map_loaded': bool(ml_predictor.valid_courses_map),
                    'model_path': getattr(ml_predictor, 'model_path', 'Not set')
                }
                logger.error(f"Model loading status: {model_status}")
                return Response({
                    "error": "Prediction models failed to load.",
                    "details": model_status
                }, status=500)
        except Exception as e:
            logger.exception("Error initializing ML predictor")
            return Response({
                "error": "Error initializing prediction service.",
                "details": str(e)
            }, status=500)

        try:
            # Create a PredictionSession instance
            prediction_session = PredictionSession.objects.create(
                student=request.user,
                year=year,
                z_score=z_score,
                stream=stream,
                district=district,
                total_predictions_generated=0,  # Will be updated after generating predictions
                confidence_level='medium'  # Default confidence level
            )

            # Get available courses/universities for the stream
            course_university_pairs = ml_predictor.get_available_courses_for_stream(stream, limit=100)  # Get more predictions
            logger.info(f"Found {len(course_university_pairs)} courses for stream: {stream}")

            if not course_university_pairs:
                logger.error(f"No courses found for stream: {stream}")
                return Response({
                    "error": f"No courses found for the selected stream: {stream}",
                    "details": f"Available streams: {list(ml_predictor.valid_courses_map.keys()) if ml_predictor.valid_courses_map else 'No streams available'}"
                }, status=400)

            predictions = []
            for i, pair in enumerate(course_university_pairs, 1):
                try:
                    course = pair['course_name']
                    university = pair['university_name']
                    logger.info(f"Processing course {i}/{len(course_university_pairs)}: {course} at {university}")

                    # Predict cutoff
                    logger.debug(f"Predicting cutoff for {course} at {university}")
                    cutoff = ml_predictor.predict_cutoff(
                        year=year,
                        university=university,
                        course_name=course,
                        district=district,
                        stream=stream,
                        aptitude_test=aptitude_test,
                        all_island_merit=all_island_merit
                    )
                    logger.debug(f"Cutoff prediction successful: {cutoff}")

                    # Predict probability
                    logger.debug(f"Predicting probability for {course} at {university}")
                    prob = ml_predictor.predict_selection_probability(
                        z_score=z_score,
                        stream=stream,
                        district=district,
                        course_name=course,
                        university=university,
                        aptitude_test=aptitude_test,
                        all_island_merit=all_island_merit
                    )
                    logger.debug(f"Probability prediction successful: {prob}")

                    predictions.append({
                        "university_name": university,
                        "course_name": course,
                        "predicted_cutoff": round(cutoff, 3),
                        "predicted_probability": round(prob, 3),
                        "recommendation": ml_predictor.get_recommendation_status(prob)
                    })
                    logger.info(f"Successfully processed course {i}/{len(course_university_pairs)}")

                except Exception as e:
                    logger.error(f"Error processing course {i} ({course} at {university}): {str(e)}", exc_info=True)
                    continue

            if not predictions:
                logger.error("No predictions could be generated due to errors")
                return Response({
                    "error": "Failed to generate any predictions. Please check the logs for details.",
                    "details": f"Tried to process {len(course_university_pairs)} courses but all failed."
                }, status=500)

            # Sort by probability
            predictions.sort(key=lambda x: x['predicted_probability'], reverse=True)

            # Update the session with the total number of predictions generated
            prediction_session.total_predictions_generated = len(predictions)
            prediction_session.save()

            return Response({
                "predictions": predictions,
                "total_predictions": len(predictions),
                "session_id": prediction_session.id,
                "message": "Predictions generated successfully!"
            })

        except Exception as e:
            return Response({"error": f"Prediction failed: {str(e)}"}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class SavePredictionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Save selected predictions"""
        if not request.user.is_student:
            return Response({"error": "Only students can save predictions."}, status=403)

        session_id = request.data.get('session_id')
        selected_predictions = request.data.get('selected_predictions', [])

        if not session_id:
            return Response({"error": "Session ID is required."}, status=400)

        if not selected_predictions:
            return Response({"error": "No predictions selected."}, status=400)

        try:
            # Verify session exists and belongs to user
            session = PredictionSession.objects.get(id=session_id, student=request.user, active=True)
            
            saved_count = 0
            for pred_data in selected_predictions:
                saved_prediction = SavedPrediction.objects.create(
                    student=request.user,
                    session=session,
                    university_name=pred_data.get('university_name', ''),
                    course_name=pred_data.get('course_name', ''),
                    predicted_cutoff=pred_data.get('predicted_cutoff', 0.0),
                    predicted_probability=pred_data.get('predicted_probability', 0.0),
                    aptitude_test_required=pred_data.get('aptitude_test_required', False),
                    all_island_merit=pred_data.get('all_island_merit', True),
                    recommendation=pred_data.get('recommendation', ''),
                    notes=pred_data.get('notes', '')
                )
                saved_count += 1

            return Response({
                "message": f"Successfully saved {saved_count} predictions!",
                "total_saved": saved_count
            })

        except PredictionSession.DoesNotExist:
            return Response({"error": "Invalid session ID or session not found."}, status=404)
        except Exception as e:
            return Response({"error": f"Failed to save predictions: {str(e)}"}, status=500)

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
    
    if user and user.is_admin and user.active:
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'admin_id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        })
    elif user and user.is_admin and not user.active:
        return Response({
            'detail': 'Account has been deactivated. Please contact another admin.'
        }, status=status.HTTP_401_UNAUTHORIZED)
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
    
    # Validate email format
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, data['email']):
        return Response({
            'email': ['Enter a valid email address.']
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get current user information"""
    if not request.user.is_student:
        return Response({"error": "Only students can access this endpoint."}, status=403)
    
    user_data = {
        'id': request.user.id,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
        'date_joined': request.user.date_joined,
        'is_active': request.user.active
    }
    
    return Response(user_data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    """Update user profile information"""
    if not request.user.is_student:
        return Response({"error": "Only students can access this endpoint."}, status=403)
    
    data = request.data
    user = request.user
    
    # Validate required fields
    required_fields = ['first_name', 'last_name', 'email']
    for field in required_fields:
        if field not in data or not data[field]:
            return Response({
                'detail': f'{field} is required'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if email is already taken by another user
    if User.objects.filter(email=data['email']).exclude(id=user.id).exists():
        return Response({
            'detail': 'Email already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Update user information
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        user.email = data['email']
        user.save()
        
        return Response({
            'detail': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'date_joined': user.date_joined,
                'is_active': user.active
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'detail': f'Profile update failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_user_password(request):
    """Change user password"""
    if not request.user.is_student:
        return Response({"error": "Only students can access this endpoint."}, status=403)
    
    data = request.data
    user = request.user
    
    # Validate required fields
    required_fields = ['current_password', 'new_password']
    for field in required_fields:
        if field not in data or not data[field]:
            return Response({
                'detail': f'{field} is required'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verify current password
    if not user.check_password(data['current_password']):
        return Response({
            'detail': 'Current password is incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Set new password
        user.set_password(data['new_password'])
        user.save()
        
        return Response({
            'detail': 'Password changed successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'detail': f'Password change failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deactivate_user_account(request):
    """Soft deactivate user account"""
    if not request.user.is_student:
        return Response({"error": "Only students can access this endpoint."}, status=403)
    
    user = request.user
    
    try:
        # Soft deactivate account
        user.active = False
        user.save()
        
        return Response({
            'detail': 'Account deactivated successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'detail': f'Account deactivation failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user_account(request):
    """Permanently delete user account and all associated data"""
    if not request.user.is_student:
        return Response({"error": "Only students can access this endpoint."}, status=403)
    
    user = request.user
    
    try:
        # Soft delete all associated data
        from .models import PredictionSession, SavedPrediction, ChatHistory, Feedback, CareerSession, SavedCareerPrediction
        
        # Soft delete predictions
        PredictionSession.objects.filter(student=user).update(active=False)
        SavedPrediction.objects.filter(student=user).update(active=False)
        
        # Soft delete chat history
        ChatHistory.objects.filter(student=user).update(active=False)
        
        # Soft delete feedback
        Feedback.objects.filter(student=user).update(active=False)
        
        # Soft delete career data
        CareerSession.objects.filter(student=user).update(active=False)
        # SavedCareerPrediction doesn't have active field, so delete permanently
        SavedCareerPrediction.objects.filter(student=user).delete()
        
        # Soft delete user account
        user.active = False
        user.is_active = False
        user.save()
        
        return Response({
            'detail': 'Account and all associated data deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'detail': f'Account deletion failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# =============================
# Admin Analytics Views
# =============================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_analytics_predictions(request):
    """Get analytics data for saved predictions"""
    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=403)
    
    try:
        from django.db.models import Count
        from .models import SavedPrediction
        
        # Get top universities
        top_universities = SavedPrediction.objects.filter(active=True).values('university_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Get popular courses
        popular_courses = SavedPrediction.objects.filter(active=True).values('course_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Get predictions by month (last 12 months)
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        months = []
        counts = []
        for i in range(11, -1, -1):
            date = timezone.now() - timedelta(days=30*i)
            month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            
            count = SavedPrediction.objects.filter(
                active=True,
                saved_at__range=(month_start, month_end)
            ).count()
            
            months.append(month_start.strftime('%b %Y'))
            counts.append(count)
        
        return Response({
            'top_universities': [{'name': item['university_name'], 'count': item['count']} for item in top_universities],
            'popular_courses': [{'name': item['course_name'], 'count': item['count']} for item in popular_courses],
            'labels': months,
            'values': counts,
            'label': 'Predictions per Month'
        })
        
    except Exception as e:
        return Response({
            'detail': f'Analytics failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_analytics_careers(request):
    """Get analytics data for career predictions"""
    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=403)
    
    try:
        from django.db.models import Count
        from .models import SavedCareerPrediction
        
        # Get top careers
        top_careers = SavedCareerPrediction.objects.values('career_title').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Get career predictions by month (last 12 months)
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        months = []
        counts = []
        for i in range(11, -1, -1):
            date = timezone.now() - timedelta(days=30*i)
            month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            
            count = SavedCareerPrediction.objects.filter(
                saved_at__range=(month_start, month_end)
            ).count()
            
            months.append(month_start.strftime('%b %Y'))
            counts.append(count)
        
        return Response({
            'top_careers': [{'title': item['career_title'], 'count': item['count']} for item in top_careers],
            'labels': months,
            'values': counts,
            'label': 'Career Predictions per Month'
        })
        
    except Exception as e:
        return Response({
            'detail': f'Analytics failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_analytics_users(request):
    """Get analytics data for user registrations"""
    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=403)
    
    try:
        from django.db.models import Count
        from .models import User
        
        # Get user registrations by month (last 12 months)
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        months = []
        counts = []
        for i in range(11, -1, -1):
            date = timezone.now() - timedelta(days=30*i)
            month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            
            count = User.objects.filter(
                active=True,
                date_joined__range=(month_start, month_end)
            ).count()
            
            months.append(month_start.strftime('%b %Y'))
            counts.append(count)
        
        return Response({
            'labels': months,
            'values': counts,
            'label': 'User Registrations per Month'
        })
        
    except Exception as e:
        return Response({
            'detail': f'Analytics failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class ModelStatusAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get status of AI models and upload processing"""
        try:
            from .utils import check_celery_worker_health
            from .models import AdminUpload
            
            # Check ML prediction models status
            ml_predictor = get_ml_predictor()
            career_predictor = get_career_predictor()
            
            ml_status = {
                'instance_created': ml_predictor is not None,
                'models_loaded': ml_predictor.models_loaded if ml_predictor else False,
                'regressor_available': ml_predictor.regressor is not None if ml_predictor else False,
                'classifier_available': ml_predictor.classifier is not None if ml_predictor else False,
                'encoders_available': (ml_predictor.feature_encoder is not None and 
                                     ml_predictor.classifier_encoder is not None) if ml_predictor else False,
                'courses_map_available': ml_predictor.valid_courses_map is not None if ml_predictor else False
            }
            
            career_status = {
                'instance_created': career_predictor is not None,
                'models_loaded': career_predictor.models_loaded if career_predictor else False,
                'hybrid_df_available': career_predictor.hybrid_df is not None if career_predictor else False,
                'occupation_df_available': career_predictor.occupation_df is not None if career_predictor else False,
                'tfidf_vectorizer_available': career_predictor.tfidf_vectorizer is not None if career_predictor else False
            }
            
            # Check if models are loaded
            models_status = {
                'embeddings_loaded': 'embeddings' in _model_cache,
                'llm_loaded': 'llm' in _model_cache,
                'vectorstore_count': len([k for k in _model_cache.keys() if k.startswith('vectorstore_')]),
                'cache_size': len(_model_cache),
                'ml_prediction_models': ml_status,
                'career_prediction_models': career_status
            }
            
            # Check upload processing status
            upload_status = {
                'celery_worker_healthy': check_celery_worker_health(),
                'pending_uploads': AdminUpload.objects.filter(processing_status='pending').count(),
                'processing_uploads': AdminUpload.objects.filter(processing_status='processing').count(),
                'completed_uploads': AdminUpload.objects.filter(processing_status='completed').count(),
                'failed_uploads': AdminUpload.objects.filter(processing_status='failed').count()
            }
            
            # Overall health check
            overall_healthy = (
                models_status['ml_prediction_models']['models_loaded'] and
                models_status['career_prediction_models']['models_loaded'] and
                upload_status['celery_worker_healthy']
            )
            
            return Response({
                'status': 'healthy' if overall_healthy else 'degraded',
                'models': models_status,
                'uploads': upload_status,
                'message': 'System status retrieved successfully' if overall_healthy else 'Some models or services are not fully operational'
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'error': str(e)
            }, status=500)

class RecommendationView(APIView):
    """API endpoint for career recommendations."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """Handles POST requests for career recommendations."""
        degree_program = request.data.get('degree_program')
        save_session = request.data.get('save_session', False)

        if not degree_program:
            return Response({"error": "Please provide a 'degree_program' in the request data."}, status=400)

        career_predictor = get_career_predictor()
        if not career_predictor or not career_predictor._ensure_models_loaded():
            return Response({"error": "Career prediction models are not available."}, status=500)

        try:
            raw_recommendations = recommend_careers_logic(
                degree_program,
                career_predictor.hybrid_df,
                None,  # occupation_tfidf_matrix is calculated within the function
                career_predictor.tfidf_vectorizer,
                career_predictor.occupation_df
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
                    "abilities": rec.get('Abilities', []),
                    "career_code": rec.get('ONET_SOC_Code', '')
                }
                recommendations.append(transformed_rec)

            # Create career session if requested and user is authenticated
            session_id = None
            if save_session and request.user.is_authenticated and request.user.is_student:
                try:
                    career_session = CareerSession.objects.create(
                        student=request.user,
                        degree_program=degree_program,
                        num_career_predictions=len(recommendations)
                    )
                    session_id = career_session.id
                    logger.info(f"Created career session {session_id} for user {request.user.email} with degree: {degree_program}")
                except Exception as e:
                    logger.error(f"Failed to create career session: {e}")
                    return Response({"error": f"Failed to save session: {str(e)}"}, status=500)

            response_data = {
                "recommendations": recommendations,
                "total_predictions": len(recommendations),
                "total_recommendations": len(recommendations),
                "message": "Career recommendations generated successfully!"
            }
            
            if session_id:
                response_data["session_id"] = session_id
                response_data["message"] += " Session saved successfully."

            return Response(response_data)

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
# User CRUD Views
# =============================
class UserViewSet(ModelViewSet):
    """CRUD operations for User model"""
    queryset = User.objects.filter(active=True)
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['user_type', 'active']
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['date_joined', 'first_name', 'last_name']
    ordering = ['-date_joined']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if is_admin_user(self.request.user):
            return User.objects.filter(active=True)
        else:
            # Students can only see their own profile
            return User.objects.filter(id=self.request.user.id, active=True)

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            if self.request.data.get('user_type') == 'admin':
                return AdminSerializer
            return StudentSerializer
        elif self.action in ['update', 'partial_update']:
            return UserProfileSerializer
        return UserSerializer

    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get current user's profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Update current user's profile"""
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['delete'])
    def deactivate_account(self, request):
        """Soft delete current user's account"""
        request.user.active = False
        request.user.save()
        return Response({"message": "Account deactivated successfully"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get user's dashboard statistics"""
        if request.user.is_student:
            stats = {
                'total_prediction_sessions': PredictionSession.objects.filter(student=request.user, active=True).count(),
                'total_saved_predictions': SavedPrediction.objects.filter(student=request.user, active=True).count(),
                'total_career_sessions': CareerSession.objects.filter(student=request.user, active=True).count(),
                'total_saved_career_predictions': SavedCareerPrediction.objects.filter(student=request.user).count(),
                'total_chats': ChatHistory.objects.filter(student=request.user, active=True).count(),
                'total_feedbacks': Feedback.objects.filter(student=request.user, active=True).count(),
            }
        else:
            stats = {
                'total_students': User.objects.filter(user_type='student', active=True).count(),
                'total_prediction_sessions': PredictionSession.objects.filter(active=True).count(),
                'total_saved_predictions': SavedPrediction.objects.filter(active=True).count(),
                'total_career_sessions': CareerSession.objects.filter(active=True).count(),
                'total_chats': ChatHistory.objects.filter(active=True).count(),
                'total_feedbacks': Feedback.objects.filter(active=True).count(),
            }
        return Response(stats)

    @action(detail=True, methods=['post'])
    def restore_account(self, request, pk=None):
        """Restore a deactivated account (admin only)"""
        if not is_admin_user(request.user):
            return Response({"error": "Admin access required"}, status=403)
        
        try:
            user = User.objects.get(pk=pk)
            user.active = True
            user.save()
            return Response({"message": "Account restored successfully"})
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user's password"""
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response({"error": "Both old and new passwords are required"}, status=400)
        
        if not request.user.check_password(old_password):
            return Response({"error": "Old password is incorrect"}, status=400)
        
        if len(new_password) < 8:
            return Response({"error": "New password must be at least 8 characters long"}, status=400)
        
        request.user.set_password(new_password)
        request.user.save()
        return Response({"message": "Password changed successfully"})

# =============================
# Prediction Session CRUD Views
# =============================
class PredictionSessionViewSet(ModelViewSet):
    """CRUD operations for PredictionSession model"""
    serializer_class = PredictionSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['stream', 'district', 'year', 'confidence_level', 'active']
    search_fields = ['stream', 'district']
    ordering_fields = ['predicted_at', 'year', 'z_score']
    ordering = ['-predicted_at']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if is_admin_user(self.request.user):
            return PredictionSession.objects.filter(active=True).select_related('student')
        else:
            # Students can only see their own sessions
            return PredictionSession.objects.filter(student=self.request.user, active=True)

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return PredictionSessionCreateSerializer
        return PredictionSessionSerializer

    def create(self, request, *args, **kwargs):
        """Create a new prediction session with required field validation"""
        # Check for required fields
        required_fields = ['year', 'z_score', 'stream', 'district']
        missing_fields = {}
        
        for field in required_fields:
            if field not in request.data or request.data[field] in [None, '', 0]:
                missing_fields[field] = ['This field is required.']
        
        if missing_fields:
            return Response(missing_fields, status=status.HTTP_400_BAD_REQUEST)
        
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Set the student when creating a session"""
        serializer.save(student=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete prediction session"""
        instance.active = False
        instance.save()
        # Also soft delete associated saved predictions
        SavedPrediction.objects.filter(session=instance).update(active=False)

    @action(detail=True, methods=['get'])
    def saved_predictions(self, request, pk=None):
        """Get saved predictions for a specific session"""
        session = self.get_object()
        saved_predictions = SavedPrediction.objects.filter(session=session, active=True)
        serializer = SavedPredictionSerializer(saved_predictions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent_sessions(self, request):
        """Get recent prediction sessions"""
        queryset = self.get_queryset()[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted session (admin only)"""
        if not is_admin_user(request.user):
            return Response({"error": "Admin access required"}, status=403)
        
        try:
            session = PredictionSession.objects.get(pk=pk)
            session.active = True
            session.save()
            return Response({"message": "Session restored successfully"})
        except PredictionSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)

# =============================
# Saved Prediction CRUD Views
# =============================
class SavedPredictionViewSet(ModelViewSet):
    """CRUD operations for SavedPrediction model"""
    serializer_class = SavedPredictionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['university_name', 'course_name', 'aptitude_test_required', 'all_island_merit', 'active']
    search_fields = ['university_name', 'course_name', 'notes']
    ordering_fields = ['saved_at', 'predicted_probability', 'predicted_cutoff']
    ordering = ['-saved_at']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if is_admin_user(self.request.user):
            return SavedPrediction.objects.filter(active=True).select_related('student', 'session')
        else:
            # Students can only see their own saved predictions
            return SavedPrediction.objects.filter(student=self.request.user, active=True).select_related('session')

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return SavedPredictionCreateSerializer
        return SavedPredictionSerializer

    def perform_create(self, serializer):
        """Set the student when creating a saved prediction"""
        serializer.save(student=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete saved prediction"""
        instance.active = False
        instance.save()

    @action(detail=False, methods=['get'])
    def by_session(self, request):
        """Get saved predictions filtered by session"""
        session_id = request.query_params.get('session_id')
        if session_id:
            queryset = self.get_queryset().filter(session_id=session_id)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return Response({"error": "session_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def high_probability(self, request):
        """Get saved predictions with high probability of selection"""
        queryset = self.get_queryset().filter(predicted_probability__gte=0.7)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted saved prediction (admin only)"""
        if not is_admin_user(request.user):
            return Response({"error": "Admin access required"}, status=403)
        
        try:
            prediction = SavedPrediction.objects.get(pk=pk)
            prediction.active = True
            prediction.save()
            return Response({"message": "Saved prediction restored successfully"})
        except SavedPrediction.DoesNotExist:
            return Response({"error": "Saved prediction not found"}, status=404)

    @action(detail=False, methods=['get'])
    def my_predictions(self, request):
        """Get current user's saved predictions"""
        if not request.user.is_student:
            return Response({"error": "Only students can view their predictions"}, status=403)
        
        queryset = self.get_queryset().filter(student=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

# =============================
# Admin Upload CRUD Views
# =============================
class AdminUploadViewSet(ModelViewSet):
    """CRUD operations for AdminUpload model"""
    serializer_class = AdminUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['processing_status', 'active']
    search_fields = ['original_filename', 'description']
    ordering_fields = ['uploaded_at', 'processed_at', 'file_size']
    ordering = ['-uploaded_at']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if is_admin_user(self.request.user):
            return AdminUpload.objects.filter(admin=self.request.user, active=True)
        else:
            # Students cannot access admin uploads
            return AdminUpload.objects.none()

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return AdminUploadCreateSerializer
        return AdminUploadSerializer

    def perform_create(self, serializer):
        """Set the admin when creating an upload"""
        serializer.save(admin=self.request.user)

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Reprocess a specific upload"""
        upload = self.get_object()
        upload.processing_status = 'pending'
        upload.save()
        
        # Start the processing task
        from .utils import ensure_pdf_processing
        ensure_pdf_processing(upload.id)
        
        return Response({"message": "Upload reprocessing started"})

    @action(detail=False, methods=['get'])
    def status_summary(self, request):
        """Get upload status summary"""
        queryset = self.get_queryset()
        summary = {
            'pending': queryset.filter(processing_status='pending').count(),
            'processing': queryset.filter(processing_status='processing').count(),
            'completed': queryset.filter(processing_status='completed').count(),
            'failed': queryset.filter(processing_status='failed').count(),
        }
        return Response(summary)

# =============================
# Chat History CRUD Views
# =============================
class ChatHistoryViewSet(ModelViewSet):
    """CRUD operations for ChatHistory model"""
    serializer_class = ChatHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['active']
    search_fields = ['question', 'answer']
    ordering_fields = ['asked_at']
    ordering = ['-asked_at']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if is_admin_user(self.request.user):
            return ChatHistory.objects.filter(active=True).select_related('student')
        else:
            # Students can only see their own chat history
            return ChatHistory.objects.filter(student=self.request.user, active=True)

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return ChatHistoryCreateSerializer
        return ChatHistorySerializer

    def perform_create(self, serializer):
        """Set the student when creating chat history"""
        serializer.save(student=self.request.user)

    @action(detail=False, methods=['get'])
    def recent_chats(self, request):
        """Get recent chat history"""
        queryset = self.get_queryset()[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search_chats(self, request):
        """Search chat history by question content"""
        query = request.query_params.get('q', '')
        if query:
            queryset = self.get_queryset().filter(question__icontains=query)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return Response({"error": "Query parameter 'q' is required"}, status=status.HTTP_400_BAD_REQUEST)

# =============================
# Feedback CRUD Views
# =============================
class FeedbackViewSet(ModelViewSet):
    """CRUD operations for Feedback model"""
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['rating', 'active']
    search_fields = ['feedback']
    ordering_fields = ['submitted_at', 'rating']
    ordering = ['-submitted_at']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if is_admin_user(self.request.user):
            return Feedback.objects.filter(active=True).select_related('student')
        else:
            # Students can see all feedbacks but can only modify their own
            return Feedback.objects.filter(active=True).select_related('student')

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action in ['create', 'update', 'partial_update']:
            return FeedbackCreateSerializer
        return FeedbackSerializer

    def perform_create(self, serializer):
        """Set the student when creating feedback"""
        serializer.save(student=self.request.user)

    def perform_update(self, serializer):
        """Check permissions before updating"""
        feedback = serializer.instance
        if not (is_admin_user(self.request.user) or feedback.student == self.request.user):
            raise permissions.PermissionDenied("You don't have permission to update this feedback")
        serializer.save()

    def perform_destroy(self, instance):
        """Soft delete feedback"""
        instance.active = False
        instance.save()

    @action(detail=False, methods=['get'])
    def my_feedback(self, request):
        """Get current user's feedback"""
        if not request.user.is_student:
            return Response({"error": "Only students can view their feedback"}, status=status.HTTP_403_FORBIDDEN)
        
        queryset = self.get_queryset().filter(student=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def rating_summary(self, request):
        """Get feedback rating summary"""
        queryset = self.get_queryset()
        summary = {
            'total': queryset.count(),
            'average_rating': queryset.aggregate(avg_rating=models.Avg('rating'))['avg_rating'],
            'rating_counts': {
                1: queryset.filter(rating=1).count(),
                2: queryset.filter(rating=2).count(),
                3: queryset.filter(rating=3).count(),
                4: queryset.filter(rating=4).count(),
                5: queryset.filter(rating=5).count(),
            }
        }
        return Response(summary)

# =============================
# Career Session CRUD Views
# =============================
class CareerSessionViewSet(ModelViewSet):
    """CRUD operations for CareerSession model"""
    serializer_class = CareerSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['active']
    search_fields = []
    ordering_fields = ['created_at', 'num_career_predictions']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if is_admin_user(self.request.user):
            return CareerSession.objects.filter(active=True).select_related('student')
        else:
            # Students can only see their own career sessions
            return CareerSession.objects.filter(student=self.request.user, active=True)

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return CareerSessionCreateSerializer
        return CareerSessionSerializer

    def perform_create(self, serializer):
        """Set the student when creating a career session"""
        serializer.save(student=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete career session"""
        instance.active = False
        instance.save()

    @action(detail=True, methods=['get'])
    def saved_predictions(self, request, pk=None):
        """Get saved career predictions for a specific session"""
        session = self.get_object()
        saved_predictions = SavedCareerPrediction.objects.filter(session=session)
        serializer = SavedCareerPredictionSerializer(saved_predictions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent_sessions(self, request):
        """Get recent career sessions"""
        queryset = self.get_queryset()[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

# =============================
# Saved Career Prediction CRUD Views
# =============================
class SavedCareerPredictionViewSet(ModelViewSet):
    """CRUD operations for SavedCareerPrediction model"""
    serializer_class = SavedCareerPredictionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        """Override create to add detailed logging"""
        logger.info(f"SavedCareerPrediction CREATE request from user: {request.user.email}")
        logger.info(f"Request data: {request.data}")
        logger.info(f"User authenticated: {request.user.is_authenticated}")
        logger.info(f"User type: {request.user.user_type}")
        
        return super().create(request, *args, **kwargs)
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['career_code', 'recommended_level']
    search_fields = ['career_title', 'career_code', 'notes']
    ordering_fields = ['saved_at', 'match_score']
    ordering = ['-saved_at']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if is_admin_user(self.request.user):
            return SavedCareerPrediction.objects.all().select_related('student', 'session')
        else:
            # Students can only see their own saved career predictions
            return SavedCareerPrediction.objects.filter(student=self.request.user).select_related('session')

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return SavedCareerPredictionCreateSerializer
        return SavedCareerPredictionSerializer

    def perform_create(self, serializer):
        """Set the student when creating a saved career prediction"""
        try:
            logger.info(f"Creating saved career prediction for user: {self.request.user.email}")
            logger.info(f"Validated data: {serializer.validated_data}")
            instance = serializer.save(student=self.request.user)
            logger.info(f"Successfully created saved career prediction: {instance.id}")
            return instance
        except Exception as e:
            logger.error(f"Error creating saved career prediction: {e}")
            raise
    
    def get_serializer_context(self):
        """Add request to serializer context for validation"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=False, methods=['get'])
    def by_session(self, request):
        """Get saved career predictions filtered by session"""
        session_id = request.query_params.get('session_id')
        if session_id:
            queryset = self.get_queryset().filter(session_id=session_id)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        return Response({"error": "session_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def high_match(self, request):
        """Get saved career predictions with high match scores"""
        queryset = self.get_queryset().filter(match_score__gte=0.7)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

