from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from .models import AdminUpload, User, ChatHistory, PredictionSession, SavedPrediction
from .tasks import process_pdf_and_create_vectorstore
import os
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
import os
import json
from functools import lru_cache
import threading
import logging
from .ml_utils import ml_predictor_instance

# Initialize logger
logger = logging.getLogger(__name__)

# Runtime tuning: faster CPU behavior and quieter tokenizers
try:
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    # Use up to half of logical cores for PyTorch ops to reduce contention on Windows
    torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
except Exception:
    pass

def clean_text(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

# Global cache for models to avoid reloading
_model_cache = {}
_cache_lock = threading.Lock()
_loading_vectorstores = set()

class ModelStatusAPIView(APIView):
    """Diagnostic endpoint to confirm ML models and encoders are loaded"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        ml = ml_predictor_instance
        info = ml.get_model_info() if hasattr(ml, 'get_model_info') else {}

        # Collect encoder class counts
        encoder_details = {}
        try:
            for key, enc in getattr(ml, 'encoders', {}).items():
                try:
                    classes = getattr(enc, 'classes_', [])
                    encoder_details[key] = {
                        'present': True,
                        'num_classes': len(classes),
                        'sample': classes[:5] if hasattr(classes, '__iter__') else []
                    }
                except Exception:
                    encoder_details[key] = {'present': True, 'num_classes': None, 'sample': []}
        except Exception:
            encoder_details = {}

        # Files present on disk
        try:
            model_dir = os.path.join(settings.BASE_DIR, 'api', 'ml_model')
            files = sorted(os.listdir(model_dir)) if os.path.isdir(model_dir) else []
        except Exception:
            files = []

        payload = {
            'models_loaded': info.get('models_loaded'),
            'regressor_available': info.get('regressor_available'),
            'classifier_available': info.get('classifier_available'),
            'scaler_available': info.get('scaler_available'),
            'available_encoders': info.get('available_encoders', []),
            'encoder_details': encoder_details,
            'model_path': info.get('model_path'),
            'model_dir_files': files,
            # Feature name diagnostics to verify PKL correctness
            'regressor_feature_names_sample': list(getattr(getattr(ml, 'regressor', None), 'feature_names_in_', [])[:30]) if getattr(ml, 'regressor', None) is not None else [],
            'regressor_feature_count': int(len(getattr(getattr(ml, 'regressor', None), 'feature_names_in_', []))) if getattr(ml, 'regressor', None) is not None else 0,
            'classifier_feature_names_sample': list(getattr(getattr(ml, 'classifier', None), 'feature_names_in_', [])[:30]) if getattr(ml, 'classifier', None) is not None else [],
            'classifier_feature_count': int(len(getattr(getattr(ml, 'classifier', None), 'feature_names_in_', []))) if getattr(ml, 'classifier', None) is not None else 0,
        }

        return Response(payload)

def get_cached_embeddings():
    """Get cached embeddings model or create new one"""
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
                # Use deterministic generation and cap output length
                max_length=512,
                max_new_tokens=256,
                do_sample=False,
                temperature=0.0,
                num_beams=1,
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

def is_vectorstore_cached(vectorstore_path: str) -> bool:
    cache_key = f'vectorstore_{vectorstore_path}'
    with _cache_lock:
        return cache_key in _model_cache

def warmup_vectorstore_async(vectorstore_path: str):
    """Kick off async warmup of vectorstore if not already loading/cached."""
    cache_key = f'vectorstore_{vectorstore_path}'
    with _cache_lock:
        if cache_key in _model_cache or vectorstore_path in _loading_vectorstores:
            return
        _loading_vectorstores.add(vectorstore_path)

    def _loader():
        try:
            get_cached_vectorstore(vectorstore_path)
        except Exception as e:
            print(f"Vectorstore warmup failed: {e}")
        finally:
            with _cache_lock:
                _loading_vectorstores.discard(vectorstore_path)

    t = threading.Thread(target=_loader, name=f"vs-warmup:{vectorstore_path}", daemon=True)
    t.start()

def warmup_models():
    """Warmup models on server start (optional)"""
    try:
        print("Warming up AI models...")
        get_cached_embeddings()
        get_cached_llm()
        # Synchronously warm latest active vectorstore so first request is instant
        try:
            latest = AdminUpload.objects.filter(active=True, processing_status='completed').latest('uploaded_at')
            if latest.vectorstore_path and os.path.exists(latest.vectorstore_path):
                _ = get_cached_vectorstore(latest.vectorstore_path)
        except Exception as e:
            print(f"Vectorstore sync warmup skipped/failed: {e}")
        print("Models warmed up successfully!")
    except Exception as e:
        print(f"Model warmup failed: {e}")
        print("Models will be loaded on first request instead.")

@method_decorator(csrf_exempt, name='dispatch')
class ReprocessPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Only admins can reprocess PDFs"}, status=403)

        try:
            # Get the latest active upload
            upload = AdminUpload.objects.filter(active=True).latest('uploaded_at')
            
            # Reset processing status
            upload.processing_status = 'pending'
            upload.save()
            
            # Start the processing task
            process_pdf_and_create_vectorstore(upload.id)
            
            return Response({"message": "PDF reprocessing started"})
            
        except AdminUpload.DoesNotExist:
            return Response({"error": "No active uploads found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AdminVerifyView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.is_staff or request.user.is_superuser:
            return Response({"isAdmin": True})
        return Response({"error": "Not an admin user"}, status=403)

@method_decorator(csrf_exempt, name='dispatch')
class AdminUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Check if user is admin
        if not (request.user.is_staff or request.user.is_superuser):
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

            # Start background processing
            # process_pdf_and_create_vectorstore.delay(upload.id)

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
        if not (request.user.is_staff or request.user.is_superuser):
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


@method_decorator(csrf_exempt, name='dispatch')
class AdminDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
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
            'uploads': uploads_data,
            'recent_predictions': predictions_data
        })


class ChatAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if user is a student
        if not request.user.is_student:
            return Response({"error": "Only students can access chat."}, status=403)
        
        # Check if student is active
        if not request.user.active:
            return Response({"error": "Student account is not active."}, status=403)

        question = request.data.get('question')
        if not question:
            return Response({"error": "Question is required."}, status=400)

        # Quick path: if user just greets, avoid running the RAG pipeline
        if re.fullmatch(r"\s*(hi|hello|hey|hola|yo|hi there|hello there)\s*", question.strip(), re.IGNORECASE):
            return Response({"answer": "Hello! Ask me anything about the university handbook and admission process."})

        # Get latest active upload/vectorstore
        try:
            active_upload = AdminUpload.objects.filter(
                active=True, 
                processing_status='completed'
            ).latest('uploaded_at')
            
            if not active_upload.vectorstore_path:
                return Response({"error": "No vectorstore found for the active handbook."}, status=500)
                
            if not os.path.exists(active_upload.vectorstore_path):
                return Response({"error": "Vectorstore files are missing."}, status=500)
                
        except AdminUpload.DoesNotExist:
            return Response({"error": "No active university handbook uploaded."}, status=500)

        # Use cached embeddings, vectorstore and LLM; if not cached yet, this will block once
        embeddings = get_cached_embeddings()
        vectorstore = get_cached_vectorstore(active_upload.vectorstore_path)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        llm = get_cached_llm()

        PROMPT_TEMPLATE = """
        You are an expert university assistant.
        Use ONLY the provided context to answer the user's question.
        - If the answer is not in the context, reply exactly: "Sorry, I don't know."
        - Answer in clear, concise English (1-3 sentences).
        - Do not include unrelated or garbled text.

        Context:
        {context}

        Question:
        {question}

        Answer:
        """
        prompt = PromptTemplate(template=PROMPT_TEMPLATE, input_variables=["context", "question"])

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff",
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt},
        )

        # Use the supported invoke() API (avoids deprecation and improves clarity)
        result = qa_chain.invoke({"query": question})
        answer = clean_text(result["result"])

        # Create chat history
        ChatHistory.objects.create(student=request.user, question=question, answer=answer)

        return Response({"answer": answer})


# Authentication views (updated for new User model)
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
    
    if user and (user.is_staff or user.is_superuser or user.is_admin):
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


class PredictionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate predictions for a student using ML models"""
        if not request.user.is_student:
            return Response({"error": "Only students can access predictions."}, status=403)

        # Step 1: Get input data
        data = request.data
        year = data.get('year')
        z_score = data.get('z_score')
        stream = data.get('stream')
        district = data.get('district')
        # Optional limit (top N to return)
        try:
            top_n = int(data.get('limit', 100))
        except (TypeError, ValueError):
            top_n = 100
        top_n = max(1, min(top_n, 100))

        # Validate input
        if not all([year, z_score, stream, district]):
            return Response({"error": "Year, Z-score, Stream, and District are required."}, status=400)
        try:
            z_score = float(z_score)
            year = int(year)
        except ValueError:
            return Response({"error": "Invalid year or Z-score format."}, status=400)

        # Step 2: Use the globally loaded ML model instance
        ml = ml_predictor_instance

        # Early validation: ensure models and encoders are available
        model_info = ml.get_model_info() if hasattr(ml, 'get_model_info') else {}
        logger.info(f"Model info: {model_info}")
        
        # Check if the required ML components are loaded
        if not model_info.get('regressor_available') or not model_info.get('classifier_available'):
            logger.error("Prediction models are not loaded. Aborting prediction request.")
            return Response({
                "error": "Prediction models are not loaded on the server.",
                "details": model_info,
            }, status=503)
        
        # Check if the required encoders are loaded
        if not model_info.get('classifier_encoder_available') or not model_info.get('feature_encoder_available'):
            logger.error("Required encoders are not loaded. Aborting prediction request.")
            return Response({
                "error": "Required encoders are not loaded on the server.",
                "details": model_info,
            }, status=503)

        # Get available courses for the stream
        available_courses = ml_predictor_instance.get_available_courses_for_stream(stream)
        
        if not available_courses:
            return Response({
                'error': f'No courses available for stream: {stream}',
                'available_streams': list(ml_predictor_instance.valid_courses_map.keys())
            }, status=400)
        
        # Create a lookup for Aptitude_Test and All_Island_Merit from historical data
        # This should come from the actual training data, but for now we'll use course-based logic
        def get_course_requirements(course_name: str, university: str) -> tuple:
            """Determine aptitude test and all-island merit requirements based on course"""
            course_lower = course_name.lower()
            university_lower = university.lower()
            
            # Medical and engineering courses typically require aptitude tests
            medical_engineering_courses = [
                'medicine', 'dental', 'veterinary', 'pharmacy', 'nursing',
                'engineering', 'architecture', 'quantity surveying', 'town planning'
            ]
            
            # Courses that typically require all-island merit
            merit_required_courses = [
                'medicine', 'dental', 'veterinary', 'pharmacy', 'engineering', 
                'architecture', 'law', 'accounting', 'business administration'
            ]
            
            # Check if course requires aptitude test
            aptitude_test = any(keyword in course_lower for keyword in medical_engineering_courses)
            
            # Check if course requires all-island merit
            all_island_merit = any(keyword in course_lower for keyword in merit_required_courses)
            
            # Special cases for specific universities
            if 'colombo' in university_lower and 'medicine' in course_lower:
                aptitude_test = True
                all_island_merit = True
            elif 'peradeniya' in university_lower and 'engineering' in course_lower:
                aptitude_test = True
                all_island_merit = True
            
            return aptitude_test, all_island_merit
        
        predictions = []
        for course in available_courses:
            # Get aptitude test and all-island merit requirements
            aptitude_test, all_island_merit = get_course_requirements(course['course_name'], course['university_name'])
            
            try:
                # Predict cutoff score
                predicted_cutoff = ml_predictor_instance.predict_cutoff(
                    year=year,
                    university=course['university_name'],
                    course_name=course['course_name'],
                    district=district,
                    stream=stream,
                    aptitude_test=aptitude_test,
                    all_island_merit=all_island_merit
                )
                
                # Predict selection probability
                predicted_probability = ml_predictor_instance.predict_selection_probability(
                    z_score=z_score,
                    stream=stream,
                    district=district,
                    course_name=course['course_name'],
                    university=course['university_name'],
                    aptitude_test=aptitude_test,
                    all_island_merit=all_island_merit
                )
                
                # Determine recommendation based on probability and Z-score
                if predicted_probability >= 0.8 and z_score >= predicted_cutoff:
                    recommendation = "Highly Recommended"
                elif predicted_probability >= 0.6 and z_score >= predicted_cutoff:
                    recommendation = "Recommended"
                elif predicted_probability >= 0.4 and z_score >= predicted_cutoff:
                    recommendation = "Moderately Recommended"
                else:
                    recommendation = "Not Recommended"
                
                predictions.append({
                    "university_name": course['university_name'],
                    "course_name": course['course_name'],
                    "predicted_cutoff": round(predicted_cutoff, 3),
                    "predicted_probability": round(predicted_probability, 3),
                    "recommendation": recommendation,
                    "aptitude_test_required": aptitude_test,
                    "all_island_merit": all_island_merit,
                    "z_score": z_score
                })
                
            except Exception as e:
                logger.error(f"Error predicting for {course['course_name']} at {course['university_name']}: {str(e)}")
                continue

        # Step 6: Update session with total predictions
        session = PredictionSession.objects.create(
            student=request.user,
            year=year,
            z_score=z_score,
            stream=stream,
            district=district
        )

        # Step 7: Sort, then build unique lists by course and by university
        predictions = sorted(predictions, key=lambda x: x['predicted_probability'], reverse=True)

        # Unique by course: keep the highest-probability entry per course_name
        best_by_course = {}
        for p in predictions:
            cname = p['course_name']
            if cname not in best_by_course or p['predicted_probability'] > best_by_course[cname]['predicted_probability']:
                best_by_course[cname] = p
        unique_by_course = list(best_by_course.values())
        unique_by_course.sort(key=lambda x: x['predicted_probability'], reverse=True)
        unique_by_course = unique_by_course[:top_n]

        # Unique by university: keep the highest-probability entry per university_name
        best_by_uni = {}
        for p in predictions:
            uname = p['university_name']
            if uname not in best_by_uni or p['predicted_probability'] > best_by_uni[uname]['predicted_probability']:
                best_by_uni[uname] = p
        unique_by_uni = list(best_by_uni.values())
        unique_by_uni.sort(key=lambda x: x['predicted_probability'], reverse=True)
        unique_by_uni = unique_by_uni[:top_n]

        return Response({
            "session_id": session.id,
            # Backward compatibility: keep 'predictions' as the unique-by-course list
            "predictions": unique_by_course,
            # Explicit fields for clarity/use in UI
            "unique_courses": unique_by_course,
            "unique_universities": unique_by_uni,
            "total_predictions": len(unique_by_course),
            "message": "Predictions generated successfully!",
            "confidence_level": "High",  # Add confidence level
            "generated_at": session.predicted_at.isoformat() if session.predicted_at else None  # Add generation timestamp
        })
class SavePredictionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Save selected predictions from a prediction session
        Frontend should send:
        - session_id: the ID returned by PredictionAPIView
        - selected_predictions: list of dicts with university_name and course_name
        """
        user = request.user
        data = request.data
        session_id = data.get('session_id')
        selected_predictions = data.get('selected_predictions', [])

        if not session_id or not selected_predictions:
            return Response({"error": "session_id and selected_predictions are required."}, status=400)

        try:
            session = PredictionSession.objects.get(id=session_id, student=user)
        except PredictionSession.DoesNotExist:
            return Response({"error": "Prediction session not found."}, status=404)

        saved_count = 0
        for pred in selected_predictions:
            university = pred.get('university_name')
            course_name = pred.get('course_name')
            if not university or not course_name:
                continue

            # Avoid duplicates
            obj, created = SavedPrediction.objects.get_or_create(
                student=user,
                university_name=university,
                course_name=course_name,
                defaults={
                    "session": session,
                    "predicted_cutoff": pred.get("predicted_cutoff"),
                    "predicted_probability": pred.get("predicted_probability"),
                    "recommendation": pred.get("recommendation", 'Not specified'),
                    "aptitude_test_required": pred.get("aptitude_test_required"),
                    "all_island_merit": pred.get("all_island_merit")
                }
            )
            if created:
                saved_count += 1

        return Response({
            "message": f"{saved_count} predictions saved successfully!",
            "total_saved": saved_count
        })



class PredictionHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Ensure only students can access
        if not hasattr(request.user, "is_student") or not request.user.is_student:
            return Response({"error": "Only students can view prediction history."}, status=403)

        # Get all active sessions for the student
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



"""
class PredictionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
       
        if not request.user.is_student:
            return Response({"error": "Only students can access predictions."}, status=403)

        # Get input data
        data = request.data
        year = data.get('year')
        z_score = data.get('z_score')
        stream = data.get('stream')
        district = data.get('district')

        # Validate input
        if not all([year, z_score, stream, district]):
            return Response({
                "error": "Year, Z-score, stream, and district are required."
            }, status=400)

        try:
            z_score = float(z_score)
            year = int(year)
        except (ValueError, TypeError):
            return Response({
                "error": "Invalid year or Z-score format."
            }, status=400)

        # Validate choices
        stream_choices = [choice[0] for choice in PredictionSession.STREAM_CHOICES]
        district_choices = [choice[0] for choice in PredictionSession.DISTRICT_CHOICES]
        
        if stream not in stream_choices:
            return Response({"error": "Invalid stream selection."}, status=400)
        if district not in district_choices:
            return Response({"error": "Invalid district selection."}, status=400)

        try:
            # Create prediction session
            session = PredictionSession.objects.create(
                student=request.user,
                year=year,
                z_score=z_score,
                stream=stream,
                district=district
            )

            # TODO: Replace this with your actual ML model prediction logic
            # This is a placeholder that generates mock predictions
            mock_predictions = self.generate_mock_predictions(z_score, stream, district)
            
            # Update session with total predictions generated
            session.total_predictions_generated = len(mock_predictions)
            session.save()

            return Response({
                "session_id": session.id,
                "predictions": mock_predictions,
                "total_predictions": len(mock_predictions),
                "message": "Predictions generated successfully!"
            })

        except Exception as e:
            return Response({
                "error": f"Prediction generation failed: {str(e)}"
            }, status=500)

    def generate_mock_predictions(self, z_score, stream, district):
      
        
        import random
        
        # Mock data - replace with r actual dataset/model
        universities = [
            "University of Colombo", "University of Peradeniya", "University of Moratuwa",
            "University of Sri Jayewardenepura", "University of Kelaniya", "University of Ruhuna"
        ]
        
        courses_by_stream = {
            "Physical Science": ["Computer Science", "Engineering", "Mathematics", "Physics"],
            "Biological Science": ["Medicine", "Pharmacy", "Veterinary Science", "Nursing"],
            "Commerce": ["Business Administration", "Accounting", "Economics", "Management"],
            "Arts": ["Law", "Psychology", "Sociology", "English Literature"],
            "Technology": ["Information Technology", "Software Engineering", "Computer Engineering"]
        }
        
        courses = courses_by_stream.get(stream, ["General Studies"])
        predictions = []
        
        for i, university in enumerate(universities):
            for j, course in enumerate(courses):
                # Generate realistic mock data
                base_cutoff = z_score - random.uniform(0.1, 0.5)
                cutoff = max(0, base_cutoff + random.uniform(-0.2, 0.2))
                
                # Calculate probability based on how student's score compares to cutoff
                if z_score >= cutoff:
                    probability = min(0.95, 0.6 + (z_score - cutoff) * 2)
                else:
                    probability = max(0.05, 0.4 - (cutoff - z_score) * 1.5)
                
                predictions.append({
                    "university_name": university,
                    "course_name": course,
                    "predicted_cutoff": round(cutoff, 3),
                    "predicted_probability": round(probability, 3),
                    "aptitude_test_required": random.choice([True, False]),
                    "all_island_merit": random.choice([True, False]),
                    "rank": len(predictions) + 1
                })
        
        # Sort by probability (highest first)
        predictions.sort(key=lambda x: x['predicted_probability'], reverse=True)
        
        # Update ranks
        for i, pred in enumerate(predictions, 1):
            pred['rank'] = i
            
        return predictions


class SavePredictionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
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


class PredictionHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        
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

"""