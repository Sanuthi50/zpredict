# tasks.py
import os
import torch
import google.generativeai as genai
from celery import shared_task
from django.conf import settings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from .models import AdminUpload, ChatHistory

# Configure Gemini once
genai.configure(api_key=settings.GEMINI_API_KEY)


def get_embeddings():
    """Helper: return HuggingFace embeddings with GPU/CPU selection."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": device}
    )


@shared_task(bind=True, max_retries=3)
def process_pdf_and_create_vectorstore(self, upload_id):
    """
    Celery task: Process PDF, split into chunks, create FAISS vectorstore,
    and save the path in the database.
    """
    try:
        upload = AdminUpload.objects.get(id=upload_id)
        upload.processing_status = "processing"
        upload.save()
        
        pdf_path = upload.pdf_file.path

        # Load PDF
        loader = PyMuPDFLoader(pdf_path)
        documents = loader.load()
        if not documents:
            upload.processing_status = "failed"
            upload.save()
            return "No content found in PDF"

        # Split into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = splitter.split_documents(documents)

        # Generate embeddings
        embeddings = get_embeddings()

        # Save FAISS vectorstore in a consistent dir
        base_vs_dir = os.path.join(settings.MEDIA_ROOT, "vectorstores")
        os.makedirs(base_vs_dir, exist_ok=True)
        vs_dir = os.path.join(base_vs_dir, f"upload_{upload_id}")
        os.makedirs(vs_dir, exist_ok=True)

        vectorstore = FAISS.from_documents(docs, embeddings)
        vectorstore.save_local(vs_dir)

        # Update DB
        upload.vectorstore_path = vs_dir
        upload.processing_status = "completed"
        upload.active = True
        upload.save()

        # Deactivate older uploads (keep history but mark inactive)
        AdminUpload.objects.exclude(id=upload_id).update(active=False)

        return "Vectorstore created successfully"

    except Exception as e:
        # Mark as failed on final retry
        if self.request.retries >= self.max_retries:
            try:
                upload = AdminUpload.objects.get(id=upload_id)
                upload.processing_status = "failed"
                upload.save()
            except:
                pass
            return f"Processing failed after {self.max_retries} retries: {str(e)}"
        
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=e, countdown=countdown)


@shared_task(bind=True, max_retries=2, time_limit=60)
def ask_question(self, student_id, question):
    """
    Celery task: Try answering with FAISS (UGC handbook).
    If no good context found, fallback to Gemini (online).
    Saves answer in ChatHistory.
    """
    try:
        from .models import User  # avoid circular import
        student = User.objects.get(id=student_id)
        context = ""
        source = "UGC Handbook"

        # Check for active handbook vectorstore
        upload = AdminUpload.objects.filter(active=True, processing_status="completed").first()
        if upload and upload.vectorstore_path:
            embeddings = get_embeddings()
            vectorstore = FAISS.load_local(
                upload.vectorstore_path, embeddings, allow_dangerous_deserialization=True
            )
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            results = retriever.get_relevant_documents(question)

            if results:
                context = "\n\n".join([doc.page_content for doc in results])
                # Prevent overloading Gemini
                context = context[:5000]

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
            student=student, question=question, answer=answer
        )

        return answer

    except Exception as e:
        err_msg = str(e).lower()
        if "quota" in err_msg or "exceeded" in err_msg:
            return "Free tier limit reached. Please try again tomorrow."
        return f"Gemini error: {e}"
