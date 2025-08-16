import os
from celery import shared_task
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import torch
from .models import AdminUpload

@shared_task(bind=True)
def process_pdf_and_create_vectorstore(self, upload_id):
    try:
        upload = AdminUpload.objects.get(id=upload_id)
        pdf_path = upload.pdf_file.path

        loader = PyMuPDFLoader(pdf_path)
        documents = loader.load()

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = splitter.split_documents(documents)

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cuda' if torch.cuda.is_available() else 'cpu'}
        )

        # Create vectorstore directory in the media folder
        vs_dir = os.path.join(os.path.dirname(pdf_path), 'vectorstores', f'upload_{upload_id}')
        os.makedirs(vs_dir, exist_ok=True)
        
        vectorstore = FAISS.from_documents(docs, embeddings)
        vectorstore.save_local(vs_dir)
        
        # Update the upload record with the vectorstore path
        upload.vectorstore_path = vs_dir
        upload.processing_status = 'completed'
        upload.save()
        vectorstore.save_local(vs_dir)

        upload.vectorstore_path = vs_dir
        upload.active = True
        upload.save()

        # Deactivate older uploads
        AdminUpload.objects.exclude(id=upload_id).update(active=False)

        return 'Vectorstore created successfully'
    except Exception as e:
        self.retry(exc=e, countdown=60, max_retries=3)
