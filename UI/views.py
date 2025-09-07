from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.http import JsonResponse
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
import jwt
from django.conf import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)


class AdminView(View):
    def get(self, request):
        return render(request, 'admin-dashboard.html')
class AdminAnalyticsView(View):
    def get(self, request):
        return render(request, 'dashboard.html')

class AdminRegisterView(View):
    def get(self, request):
        return render(request, 'admin-register.html')
class AdminReprocessView(View):
    def get(self, request):
        logger.info("=== AdminReprocessView: Starting token validation ===")
        
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        logger.info(f"Authorization header: {auth_header}")
        
        token = None
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            logger.info(f"Token extracted from Authorization header: {token[:20]}..." if token else "None")
        else:
            logger.info("No Bearer token in Authorization header, checking cookies and GET params")
            # Fallback: Check cookies and GET parameters for direct access
            cookie_token = request.COOKIES.get('admin_token')
            get_token = request.GET.get('token')
            
            logger.info(f"Cookie token: {cookie_token[:20] + '...' if cookie_token else 'None'}")
            logger.info(f"GET token: {get_token[:20] + '...' if get_token else 'None'}")
            
            token = cookie_token or get_token
        
        logger.info(f"Final token to validate: {token[:20] + '...' if token else 'None'}")
        
        if not token:
            logger.warning("No token found anywhere - redirecting to admin-dashboard")
            return redirect('admin-dashboard')
        
        try:
            logger.info("Attempting to validate token with UntypedToken")
            # Validate token and get user
            validated_token = UntypedToken(token)
            logger.info("Token validation with UntypedToken successful")
            
            logger.info("Attempting to decode token with jwt.decode")
            # Decode token to get user info
            decoded_token = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=['HS256']
            )
            logger.info(f"Token decoded successfully. Payload: {decoded_token}")
            
            user_id = decoded_token.get('user_id')
            logger.info(f"Extracted user_id: {user_id}")
            
            if not user_id:
                logger.warning("No user_id found in token - redirecting to admin-dashboard")
                return redirect('admin-dashboard')
            
            # Get user and check if they're admin
            try:
                logger.info(f"Attempting to get user with id: {user_id}")
                user = User.objects.get(id=user_id)
                logger.info(f"User found: {user.username}, is_staff: {user.is_staff}, is_superuser: {user.is_superuser}")
                
                if not (user.is_staff or user.is_superuser):
                    logger.warning(f"User {user.username} is not admin - redirecting to admin-dashboard")
                    return redirect('admin-dashboard')
                    
            except User.DoesNotExist:
                logger.error(f"User with id {user_id} does not exist - redirecting to admin-dashboard")
                return redirect('admin-dashboard')
            
            # Token is valid and user is admin, render the page
            logger.info(f"All checks passed! Rendering reprocess.html for user: {user.username}")
            return render(request, 'reprocess.html', {
                'user': user,
                'is_admin': True
            })
            
        except InvalidToken as e:
            logger.error(f"InvalidToken error: {str(e)} - redirecting to admin-dashboard")
            return redirect('admin-dashboard')
        except TokenError as e:
            logger.error(f"TokenError: {str(e)} - redirecting to admin-dashboard")
            return redirect('admin-dashboard')
        except jwt.ExpiredSignatureError as e:
            logger.error(f"JWT ExpiredSignatureError: {str(e)} - redirecting to admin-dashboard")
            return redirect('admin-dashboard')
        except jwt.InvalidTokenError as e:
            logger.error(f"JWT InvalidTokenError: {str(e)} - redirecting to admin-dashboard")
            return redirect('admin-dashboard')
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {str(e)} - redirecting to admin-dashboard")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return redirect('admin-dashboard')
class FeedbackManagementView(View):
    def get(self, request):
        return render(request, 'feedback-management.html')

class AdminProfileView(View):
    def get(self, request):
        return render(request, 'adminprofile.html')

class AdminLoginView(View):
    def get(self, request):
        return render(request, 'admin-login.html')





