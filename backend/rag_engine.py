"""
Enhanced RAG Engine with Conversation Memory and Groq API
Handles vector database, semantic search, conversation history, and response generation
"""
import json
import os
import pickle
import random
import time
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import requests
from groq import Groq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
import warnings
import re
from deep_translator import GoogleTranslator

# Suppress noisy warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="Failed to initialize NumPy")

# Load environment variables
load_dotenv()


class ConversationMemory:
    """Manages conversation history for context-aware responses"""
    
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.conversations = {}  # session_id -> list of messages
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to conversation history"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        self.conversations[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last max_history messages
        if len(self.conversations[session_id]) > self.max_history:
            self.conversations[session_id] = self.conversations[session_id][-self.max_history:]
    
    def get_history(self, session_id: str, last_n: int = 5) -> List[Dict]:
        """Get conversation history for a session"""
        if session_id not in self.conversations:
            return []
        return self.conversations[session_id][-last_n:]
    
    def clear_session(self, session_id: str):
        """Clear conversation history for a session"""
        if session_id in self.conversations:
            del self.conversations[session_id]


class RAGEngine:
    def __init__(self, data_path: str = "data.json", ollama_url: str = "http://localhost:11434"):
        self.data_path = data_path
        self.ollama_url = ollama_url
        
        # Initialize Groq API
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            try:
                self.groq_client = Groq(api_key=api_key)
                print("✅ Groq API configured")
            except Exception as e:
                print(f"❌ Groq configuration failed: {e}")
                self.groq_client = None
        else:
            print("⚠️ GROQ_API_KEY not found. LLM features will be disabled.")
            self.groq_client = None

        # Initialize Sentence Transformers for embeddings.
        # Render free instances are memory constrained; use a lighter default there.
        try:
            from sentence_transformers import SentenceTransformer
            render_env = os.getenv("RENDER", "").lower() == "true"
            model_name = os.getenv(
                "EMBEDDING_MODEL_NAME",
                "sentence-transformers/all-MiniLM-L6-v2" if render_env else "sentence-transformers/all-mpnet-base-v2",
            )
            self.embedding_model = SentenceTransformer(model_name)
            print(f"✅ Sentence Transformers embeddings initialized ({model_name})")
        except Exception as e:
            print(f"❌ Failed to initialize embeddings: {e}")
            raise

        # Qdrant Cloud setup
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        qdrant_collection = os.getenv("QDRANT_COLLECTION_NAME", "uit_rag")
        
        print(f"[Qdrant] URL set: {bool(qdrant_url)} | COLLECTION: {qdrant_collection}")
        
        if not qdrant_url or not qdrant_api_key:
            raise RuntimeError("QDRANT_URL and QDRANT_API_KEY must be set in environment variables.")
        
        try:
            # Initialize Qdrant client
            self.qdrant_client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key
            )
            self.collection_name = qdrant_collection
            
            print(f"✅ Connected to Qdrant collection: {qdrant_collection}")
            
            # Get collection info to verify connection
            collection_info = self.qdrant_client.get_collection(collection_name=qdrant_collection)
            print(f"✅ Collection stats: {collection_info.points_count} vectors")
            
        except Exception as e:
            print(f"❌ Qdrant initialization failed: {e}")
            raise

        self.documents = []
        self.metadatas = []
        # Conversation memory
        self.memory = ConversationMemory(max_history=20)
        
        # Skip database initialization - data already in Qdrant
        print("✅ Using existing Qdrant data (skipping upload)")
    
    def _initialize_database(self):
        """Load university data and create embeddings, then upsert to Pinecone"""
        print("Initializing database with university data (Pinecone)...")
        with open(self.data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        documents = []
        metadatas = []

        # Process university info
        uni_info = data.get('university_info', {})
        doc = f"University: {uni_info.get('name')}. {uni_info.get('motto')}. Located at {uni_info.get('location')}. Established in {uni_info.get('established')}. Contact: {uni_info.get('phone')}, {uni_info.get('email')}"
        documents.append(doc)
        metadatas.append({"type": "university_info", "category": "general"})

        # Process faculties - with detailed info
        for faculty in data.get('faculties', []):
            doc = f"Faculty: {faculty.get('name')}. Dean: {faculty.get('dean')}. Programs offered: {', '.join(faculty.get('programs', []))}. Specializations: {', '.join(faculty.get('specializations', []))}. Total students: {faculty.get('total_students')}. Faculty members: {faculty.get('faculty_count')}. Contact: {faculty.get('email')}, {faculty.get('phone')}"
            documents.append(doc)
            metadatas.append({"type": "faculty", "faculty_id": faculty.get('id'), "category": "academic", "name": faculty.get('name')})

            # Separate document for dean info (for better retrieval)
            dean_doc = f"The dean of {faculty.get('name')} is {faculty.get('dean')}. Contact: {faculty.get('email')}, {faculty.get('phone')}"
            documents.append(dean_doc)
            metadatas.append({"type": "dean_info", "faculty_id": faculty.get('id'), "category": "faculty", "dean": faculty.get('dean')})

        # Process courses
        for course in data.get('courses', []):
            doc = f"Course: {course.get('name')} ({course.get('code')}). Faculty: {course.get('faculty')}. Credits: {course.get('credits')}. Year {course.get('year')}, Semester {course.get('semester')}. Instructor: {course.get('instructor')}. Schedule: {course.get('schedule')}. Room: {course.get('room')}. Prerequisites: {course.get('prerequisites')}. Description: {course.get('description')}"
            documents.append(doc)
            metadatas.append({"type": "course", "code": course.get('code'), "category": "academic"})

        # Process faculty members
        for member in data.get('faculty_members', []):
            doc = f"Faculty Member: {member.get('name')} ({member.get('designation')}). Specialization: {member.get('specialization')}. Faculty: {member.get('faculty')}. Qualification: {member.get('qualification')}. Experience: {member.get('experience_years')} years. Office: {member.get('office')}. Office hours: {member.get('office_hours')}. Contact: {member.get('email')}, {member.get('phone')}"
            documents.append(doc)
            metadatas.append({"type": "faculty_member", "id": member.get('id'), "category": "faculty"})

        # Process facilities
        for facility in data.get('facilities', []):
            doc = f"Facility: {facility.get('name')}. Location: {facility.get('location')}. Capacity: {facility.get('capacity')}. Timings: {facility.get('timings')}. Amenities: {', '.join(facility.get('amenities', []))}. Contact: {facility.get('contact')}"
            documents.append(doc)
            metadatas.append({"type": "facility", "category": "infrastructure", "name": facility.get('name')})

        # Process FAQs
        for faq in data.get('faqs', []):
            doc = f"Question: {faq.get('question')} Answer: {faq.get('answer')} Category: {faq.get('category')}"
            documents.append(doc)
            metadatas.append({"type": "faq", "category": faq.get('category', 'general').lower()})

        # Process academic calendar
        for event in data.get('academic_calendar', []):
            doc = f"Event: {event.get('event')}. Date: {event.get('start_date')} to {event.get('end_date')}. Description: {event.get('description')}"
            documents.append(doc)
            metadatas.append({"type": "calendar", "category": "academic"})

        print(f"Creating embeddings for {len(documents)} documents...")
        embeddings = self.embedding_model.encode(documents, show_progress_bar=True)
        embeddings = np.array(embeddings).astype('float32')

        # Upsert to Pinecone
        pinecone_vectors = []
        for i, (embedding, doc, meta) in enumerate(zip(embeddings, documents, metadatas)):
            pinecone_vectors.append({
                "id": f"doc-{i}",
                "values": embedding.tolist(),
                "metadata": {"content": doc, **meta}
            })
        # Pinecone upsert in batches (max 100 per batch)
        batch_size = 100
        for i in range(0, len(pinecone_vectors), batch_size):
            batch = pinecone_vectors[i:i+batch_size]
            self.pinecone_index.upsert(vectors=batch)

        self.documents = documents
        self.metadatas = metadatas
        print("Database initialization complete! (Pinecone)")
    
    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents using Qdrant with Sentence Transformers embeddings"""
        # Create query embedding using Sentence Transformers (768 dimensions)
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Query Qdrant using query_points (newer API)
        search_results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=n_results,
            with_payload=True
        )
        
        # Format results
        retrieved_docs = []
        for hit in search_results.points:
            payload = hit.payload or {}
            content = payload.get("content", payload.get("text", ""))
            
            # Extract metadata
            metadata = {k: v for k, v in payload.items() if k not in ["content", "text"]}
            
            retrieved_docs.append({
                "content": content,
                "metadata": metadata,
                "distance": hit.score
            })
        
        return retrieved_docs

    def _detect_and_translate(self, query: str, language: str) -> str:
        """
        Detect if query needs translation and translate to English for better search results
        Returns: translated query (or original if already in English)
        """
        # If user explicitly selected Hindi or query contains Hindi characters, translate
        if language == "Hindi" or any('\u0900' <= char <= '\u097F' for char in query):
            try:
                print(f"  🔤 Translating Hindi query to English for better search...")
                translator = GoogleTranslator(source='hi', target='en')
                translated = translator.translate(query)
                print(f"     Original (Hindi): {query}")
                print(f"     Translated (English): {translated}")
                return translated
            except Exception as e:
                print(f"  ⚠️  Translation failed ({e}), using original query")
                return query
        
        return query
    
    def _check_needs_clarification(self, query: str, context_docs: List[Dict[str, Any]], conversation_history: List[Dict] = None) -> tuple[bool, str]:
        """
        Check if query is ambiguous and needs clarification
        Returns: (needs_clarification: bool, clarification_message: str)
        """
        query_lower = query.lower().strip()
        
        # Define ambiguous query patterns
        ambiguous_patterns = {
            'faculty': {
                'keywords': ['faculty', 'professor', 'teacher', 'instructor', 'staff', 'dr', 'dr.'],
                'clarification_en': "I found faculty information for multiple programs. Which program would you like to know about?\n\n• B.Tech Computer Science and Engineering\n• B.Tech AI and Machine Learning\n• B.Tech Data Science\n• B.Tech Cyber Security\n• B.Tech Electronics & Communication\n\nPlease specify the program name.",
                'clarification_hi': "मुझे कई कार्यक्रमों के लिए संकाय जानकारी मिली। आप किस कार्यक्रम के बारे में जानना चाहेंगे?\n\n• B.Tech Computer Science and Engineering\n• B.Tech AI and Machine Learning\n• B.Tech Data Science\n• B.Tech Cyber Security\n• B.Tech Electronics & Communication\n\nकृपया कार्यक्रम का नाम बताएं।"
            },
            'admission': {
                'keywords': ['admission', 'admissions', 'apply', 'application', 'eligibility', 'entrance'],
                'clarification_en': "I can help with admission information. Which program are you interested in?\n\n• B.Tech programs\n• M.Tech programs\n• MBA programs\n• Other undergraduate programs\n\nPlease specify the program.",
                'clarification_hi': "मैं प्रवेश जानकारी में मदद कर सकता हूं। आप किस कार्यक्रम में रुचि रखते हैं?\n\n• B.Tech कार्यक्रम\n• M.Tech कार्यक्रम\n• MBA कार्यक्रम\n• अन्य स्नातक कार्यक्रम\n\nकृपया कार्यक्रम बताएं।"
            },
            'fees': {
                'keywords': ['fee', 'fees', 'cost', 'tuition', 'payment', 'scholarship'],
                'clarification_en': "I can provide fee information. Which program are you asking about?\n\n• B.Tech programs\n• M.Tech programs\n• MBA programs\n• Other programs\n\nPlease specify the program.",
                'clarification_hi': "मैं शुल्क जानकारी प्रदान कर सकता हूं। आप किस कार्यक्रम के बारे में पूछ रहे हैं?\n\n• B.Tech कार्यक्रम\n• M.Tech कार्यक्रम\n• MBA कार्यक्रम\n• अन्य कार्यक्रम\n\nकृपया कार्यक्रम बताएं।"
            },
            'syllabus': {
                'keywords': ['syllabus', 'curriculum', 'course', 'subjects', 'topics'],
                'clarification_en': "I can help with syllabus information. Which program's syllabus would you like to know about?\n\nPlease specify the program name (e.g., B.Tech AI/ML, B.Tech Data Science).",
                'clarification_hi': "मैं पाठ्यक्रम जानकारी में मदद कर सकता हूं। आप किस कार्यक्रम का पाठ्यक्रम जानना चाहेंगे?\n\nकृपया कार्यक्रम का नाम बताएं (जैसे, B.Tech AI/ML, B.Tech Data Science)।"
            }
        }
        
        # Check if query matches any ambiguous pattern
        for pattern_type, pattern_data in ambiguous_patterns.items():
            # Check if any keyword matches
            if any(keyword in query_lower for keyword in pattern_data['keywords']):
                # Check if query is too generic (no program mentioned)
                program_keywords = ['ai', 'ml', 'machine learning', 'data science', 'cyber security', 
                                  'computer science', 'cse', 'ece', 'electronics', 'communication',
                                  'fintech', 'cloud', 'google', 'ibm', 'paytm', 'uit']
                
                # Keywords that should BYPASS clarification because they are general/universal
                general_bypass_keywords = ['transport', 'bus', 'medical', 'ambulance', 'hostel', 
                                         'cafeteria', 'mess', 'wifi', 'internet', 'library']
                
                has_program_context = any(prog in query_lower for prog in program_keywords)
                has_general_bypass = any(gen in query_lower for gen in general_bypass_keywords)
                
                # If it's a general topic, we don't need program clarification
                if has_general_bypass:
                    continue
                
                # Check conversation history for program context
                has_history_context = False
                if conversation_history:
                    for msg in conversation_history[-3:]:  # Check last 3 messages
                        if any(prog in msg.get('content', '').lower() for prog in program_keywords):
                            has_history_context = True
                            break
                
                # Check if we already have a high-confidence general answer in context_docs
                has_general_answer = False
                if context_docs:
                    top_doc = context_docs[0]
                    top_metadata = top_doc.get('metadata', {})
                    top_score = top_doc.get('distance', top_doc.get('score', 0))
                    top_program = top_metadata.get('program', top_metadata.get('program_title'))
                    # If top document is "ALL" or "ALL_UIT" and has a high score (>0.55), 
                    # we probably don't need clarification
                    if top_score > 0.55 and top_program in ['ALL', 'ALL_UIT']:
                        has_general_answer = True

                # If no program context AND no good general answer, ask for clarification
                if not has_program_context and not has_history_context and not has_general_answer:
                    # Determine language
                    lang_key = 'clarification_en'  # Default to English
                    if any(hindi_word in query_lower for hindi_word in ['संकाय', 'प्रवेश', 'शुल्क']):
                        lang_key = 'clarification_hi'
                    
                    print(f"🔍 Ambiguous query detected: '{pattern_type}' without program context")
                    return (True, pattern_data[lang_key])
        
        # Check if retrieved documents are too diverse (multiple programs)
        if len(context_docs) >= 3:
            programs = set()
            for doc in context_docs:
                if 'metadata' in doc and 'program_title' in doc['metadata']:
                    programs.add(doc['metadata']['program_title'])
            
            # If more than 2 different programs, need clarification
            if len(programs) > 2:
                print(f"🔍 Multiple programs detected in results: {len(programs)} programs")
                return (True, "I found information about multiple programs. Could you please specify which program you're interested in?\n\nFor example:\n• B.Tech AI/ML\n• B.Tech Data Science\n• B.Tech Cyber Security\n• B.Tech Computer Science\n\nPlease specify the program name.")
        
        # No clarification needed
        return (False, "")
    
    def _is_followup_answer(self, query: str, conversation_history: List[Dict]) -> tuple[bool, str]:
        """
        Detect if query is a follow-up answer to a clarification question
        Returns: (is_followup: bool, reconstructed_query: str)
        """
        if not conversation_history or len(conversation_history) < 2:
            return (False, "")
        
        # Get last assistant message
        last_bot_msg = None
        for msg in reversed(conversation_history):
            if msg['role'] == 'assistant':
                last_bot_msg = msg['content']
                break
        
        if not last_bot_msg:
            return (False, "")
        
        # Check if last message was a clarification
        clarification_indicators = [
            "which program",
            "please specify",
            "which one",
            "could you specify",
            "tell me more about",
            "specify the program"
        ]
        
        is_clarification = any(ind in last_bot_msg.lower() for ind in clarification_indicators)
        
        if not is_clarification:
            return (False, "")
        
        # Check if current query is short (likely an answer)
        query_lower = query.lower().strip()
        is_short = len(query.split()) <= 6  # Short answers
        
        # Check if it mentions a program
        program_keywords = ['btech', 'b.tech', 'b tech', 'mtech', 'm.tech', 'mba', 
                           'ai', 'ml', 'aiml', 'data science', 'cyber', 'cse', 'ece',
                           'computer science', 'electronics', 'fintech', 'cloud']
        mentions_program = any(kw in query_lower for kw in program_keywords)
        
        if is_short and mentions_program:
            # Find original intent from history (skip the last clarification)
            for msg in reversed(conversation_history[:-1]):
                if msg['role'] == 'user':
                    original_query = msg['content']
                    # Reconstruct: original intent + program specification
                    reconstructed = f"{original_query} for {query}"
                    print(f"🔗 Detected follow-up answer to clarification")
                    print(f"   Original query: '{original_query}'")
                    print(f"   User answer: '{query}'")
                    print(f"   Reconstructed: '{reconstructed}'")
                    return (True, reconstructed)
        
        return (False, "")
    
    def generate_response(self, query: str, context_docs: List[Dict[str, Any]], language: str = "English", conversation_history: List[Dict] = None) -> str:
        """Generate response using Ollama with conversation context and greeting handling"""
        
        print("\n" + "="*80)
        print("🔍 RAG PIPELINE - STEP-BY-STEP PROCESS")
        print("="*80)
        print(f"📝 User Query: '{query}'")
        print(f"🌐 Language: {language}")
        print(f"📚 Retrieved Documents: {len(context_docs)}")
        
        # Check if this is a follow-up answer (to avoid infinite clarification loop)
        is_followup_answer, _ = self._is_followup_answer(query, conversation_history or [])
        
        # STEP 0: CLARIFICATION DETECTION - Check if query needs more context
        print("\n" + "-"*80)
        print("STEP 0: CLARIFICATION DETECTION")
        print("-"*80)
        
        if is_followup_answer:
            print("✅ Query is a follow-up answer - skipping clarification check")
        else:
        
            needs_clarification, clarification_msg = self._check_needs_clarification(query, context_docs, conversation_history)
        
            if needs_clarification:
                print(f"❓ Ambiguous query detected - asking for clarification")
                print(f"✅ Clarification prompt: {clarification_msg[:100]}...")
                print("="*80 + "\n")
                return clarification_msg
            else:
                print("✅ Query is specific enough - proceeding")
        
        # DYNAMIC CONVERSATION HANDLING (Greetings & Fillers)
        conversational_keywords = {
            'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings'],
            'goodbye': ['good night', 'goodbye', 'bye', 'see you', 'शुभ रात्रि', 'अलविदा'],
            'filler': ['ok', 'okay', 'cool', 'thanks', 'thank you', 'fine', 'understand', 'got it']
        }
        
        query_lower = query.lower().strip()
        is_conversational = False
        conv_type = "general"
        
        # Check if query is a pure conversational query (short and matches keywords)
        words = query_lower.split()
        if len(words) <= 3:
            for c_type, keywords in conversational_keywords.items():
                if any(re.search(rf"\b{re.escape(kw)}\b", query_lower) for kw in keywords):
                    is_conversational = True
                    conv_type = c_type
                    break

        if is_conversational:
            print(f"\n✅ DYNAMIC CONVERSATION DETECTED: {conv_type}")
            try:
                # Use a specific prompt for conversational responses
                conv_prompt = f"""You are a friendly and enthusiastic student advisor at Karnavati University's UIT campus.
                
The student just said: "{query}"
Context: {conv_type}

Your Response Guidelines:
- Be warm, welcoming, and conversational (like a helpful friend, not a robot!)
- For greetings: Welcome them with genuine enthusiasm and invite them to ask about programs, admissions, campus life, or anything else
- For thanks/acknowledgments: Acknowledge warmly and suggest 2-3 interesting topics they might want to explore (e.g., "Cool! Want to know about our placement records? Or maybe campus facilities?")
- Keep it natural and brief (2-3 sentences max)
- Use emojis sparingly for friendliness (1-2 max)
- Respond in {language}
- Sound human - avoid phrases like "as an AI" or overly formal language

Make it conversational and engaging!
"""
                
                # Use Groq for dynamic responses
                if self.groq_client:
                    chat_completion = self.groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": "You are a friendly student advisor at Karnavati University's UIT campus."},
                            {"role": "user", "content": conv_prompt}
                        ],
                        model="llama-3.3-70b-versatile",
                        temperature=0.7,
                        max_tokens=150,
                    )
                    answer = chat_completion.choices[0].message.content.strip()
                    print(f"✅ Dynamic Response: {answer}")
                    return answer
                else:
                    raise Exception("Groq client not configured")
            except Exception as e:
                print(f"⚠️ Dynamic fallback failed: {e}")
                # Better fallback responses
                fallbacks = [
                    "Hey! I'm here to help with anything about UIT - programs, admissions, campus life, you name it! What would you like to know? 😊",
                    "What's up! Feel free to ask me about courses, fees, placements, or anything else about UIT! 🎓",
                    "Hi there! I can help you with info about our programs, facilities, admissions - just ask away! 💡"
                ]
                return random.choice(fallbacks)
        
        # Build context from retrieved documents
        print("\n" + "-"*80)
        print("STEP 2: CONTEXT BUILDING")
        print("-"*80)
        print(f"📄 Building context from {len(context_docs)} retrieved documents...")
        
        # Use all retrieved documents for comprehensive answers
        context = "\n\n".join([doc['content'] for doc in context_docs])
        
        # Show retrieved documents
        for i, doc in enumerate(context_docs, 1):
            print(f"\n  Document {i}:")
            print(f"    Content preview: {doc['content'][:100]}...")
            if 'metadata' in doc:
                meta = doc['metadata']
                if 'program_title' in meta:
                    print(f"    Program: {meta['program_title']}")
                if 'section_type' in meta:
                    print(f"    Section: {meta['section_type']}")
                if 'source_url' in meta:
                    print(f"    Source: {meta['source_url'][:60]}...")
        
        # Build conversation history context
        history_context = ""
        if conversation_history and len(conversation_history) > 0:
            print(f"\n📜 Including {len(conversation_history[-5:])} previous messages for context")
            history_context = "\n\nPrevious conversation:\n"
            for msg in conversation_history[-5:]:  # Last 5 messages
                role = "Student" if msg['role'] == 'user' else "Assistant"
                history_context += f"{role}: {msg['content']}\n"
        
        
        # Language-specific instructions with STRONG enforcement
        language_instructions = {
            "Hindi": "You MUST answer ONLY in Hindi language. हिंदी में जवाब दें। Do not use any other language.",
            "English": "You MUST answer ONLY in English language. Do not use any other language."
        }
        
        lang_instruction = language_instructions.get(language, "Answer in English")
        
        # Create prompt for natural, conversational answers
        prompt = f"""You are a friendly student assistant at UIT (Unitedworld Institute of Technology) - the engineering college at Karnavati University.

IMPORTANT: UIT is ONLY for engineering programs. If someone asks about law, management, design, or other non-engineering departments, politely tell them this bot is specifically for UIT engineering students and they should contact the main university office for other programs.

RULES:
1. LANGUAGE: {lang_instruction}
2. Talk naturally like a human, not like Wikipedia or a formal document
3. Give only the KEY POINTS the person needs to know
4. Keep it brief and conversational - 2-4 sentences maximum
5. Use the information from Context but say it in a natural, helpful way
6. Don't use numbered lists or bullet points - just talk normally
7. If the Context doesn't have relevant info for their question, say you don't have that information

Context:
{context}

Question: {query}

Give a brief, natural answer with just the key points they need to know.

Answer (in {language}):"""
        
        print("\n" + "-"*80)
        print("STEP 3: GROQ API CALL")
        print("-"*80)
        
        try:
            # Use Groq API for response generation
            if not self.groq_client:
                print("❌ Groq API not configured")
                return "Error: Groq API not configured. Please set GROQ_API_KEY."
            
            print("🤖 Calling Groq API...")
            print(f"   Model: llama-3.3-70b-versatile")
            print(f"   Temperature: 0.5")
            print(f"   Max tokens: 250")
            
            # Generate response using Groq
            print("⏳ Generating response...")
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a friendly student helper at UIT (Unitedworld Institute of Technology) - the engineering college at Karnavati University. You ONLY have information about UIT engineering programs (B.Tech in CSE, AIML, Data Science, Cyber Security, ECE). If asked about law, management, design, or other departments, politely clarify that you're specifically for UIT engineering and they should contact the main university office. Talk like a real person helping another student - natural, brief, and to the point. Give only key information they need in 2-4 sentences. No lists, no formal language, just helpful conversation. Use only the provided context."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.5,
                max_tokens=250,
                top_p=0.9,
            )
            
            answer = chat_completion.choices[0].message.content.strip()
            
            # Log for debugging
            print(f"Query in {language}: {query[:50]}...")
            print(f"Response preview: {answer[:100]}...")
            
            print("\n" + "-"*80)
            print("STEP 4: RESPONSE GENERATED")
            print("-"*80)
            print(f"✅ Response length: {len(answer)} characters")
            print(f"✅ Response preview: {answer[:150]}...")
            print("="*80 + "\n")
            
            return answer
        
        except Exception as e:
            print(f"\n❌ Error calling Groq API: {e}")
            print("="*80 + "\n")
            # Fallback: return first complete sentence from context
            sentences = context.split('.')
            if sentences:
                # Return first complete sentence
                return sentences[0].strip() + "."
            return f"I apologize, but I'm having trouble generating a response. Please try again."
    
    def query(self, question: str, language: str = "English", session_id: str = "default") -> Dict[str, Any]:
        """Main query method with conversation memory and follow-up understanding"""
        # Get conversation history
        history = self.memory.get_history(session_id, last_n=5)
        
        # Check if this is a follow-up answer to a clarification
        is_followup, reconstructed_query = self._is_followup_answer(question, history)
        
        if is_followup:
            # Use reconstructed query for search
            search_query = reconstructed_query
            print(f"🔄 Using reconstructed query for search: '{search_query}'")
        else:
            search_query = question
        
        # IMPORTANT: Translate Hindi queries to English for better search results
        # The vector database contains English documents, so we search in English
        translated_query = self._detect_and_translate(search_query, language)
        
        # Search for relevant documents using the translated query
        relevant_docs = self.search(translated_query, n_results=3)
        
        # Generate response with conversation context (in the requested language)
        answer = self.generate_response(question, relevant_docs, language, history)
        
        # Save to conversation memory
        self.memory.add_message(session_id, "user", question)
        self.memory.add_message(session_id, "assistant", answer)
        
        return {
            "question": question,
            "answer": answer,
            "sources": relevant_docs,
            "language": language,
            "session_id": session_id
        }

    def stream_query(self, question: str, language: str = "English", session_id: str = "default") -> Iterator[Dict[str, Any]]:
        """Stream query response as incremental events for SSE consumers."""
        started_at = time.perf_counter()
        print(f"🌊 stream_query start | session={session_id} | lang={language} | q='{question[:60]}'")
        history = self.memory.get_history(session_id, last_n=5)

        is_followup, reconstructed_query = self._is_followup_answer(question, history)
        search_query = reconstructed_query if is_followup else question

        translated_query = self._detect_and_translate(search_query, language)
        relevant_docs = self.search(translated_query, n_results=3)

        yield {
            "event": "meta",
            "question": question,
            "language": language,
            "sources": relevant_docs,
        }

        if not is_followup:
            needs_clarification, clarification_msg = self._check_needs_clarification(question, relevant_docs, history)
            if needs_clarification:
                self.memory.add_message(session_id, "user", question)
                self.memory.add_message(session_id, "assistant", clarification_msg)
                yield {"event": "delta", "text": clarification_msg}
                yield {
                    "event": "done",
                    "answer": clarification_msg,
                    "sources": relevant_docs,
                    "language": language,
                    "session_id": session_id,
                }
                return

        context = "\n\n".join([doc["content"] for doc in relevant_docs])

        language_instructions = {
            "Hindi": "You MUST answer ONLY in Hindi language. हिंदी में जवाब दें। Do not use any other language.",
            "English": "You MUST answer ONLY in English language. Do not use any other language.",
        }
        lang_instruction = language_instructions.get(language, "Answer in English")

        prompt = f"""You are a friendly student assistant at UIT (Unitedworld Institute of Technology) - the engineering college at Karnavati University.

IMPORTANT: UIT is ONLY for engineering programs. If someone asks about law, management, design, or other non-engineering departments, politely tell them this bot is specifically for UIT engineering students and they should contact the main university office for other programs.

RULES:
1. LANGUAGE: {lang_instruction}
2. Talk naturally like a human, not like Wikipedia or a formal document
3. Give only the KEY POINTS the person needs to know
4. Keep it brief and conversational - 2-4 sentences maximum
5. Use the information from Context but say it in a natural, helpful way
6. Don't use numbered lists or bullet points - just talk normally
7. If the Context doesn't have relevant info for their question, say you don't have that information

Context:
{context}

Question: {question}

Give a brief, natural answer with just the key points they need to know.

Answer (in {language}):"""

        if not self.groq_client:
            answer = self.generate_response(question, relevant_docs, language, history)
            self.memory.add_message(session_id, "user", question)
            self.memory.add_message(session_id, "assistant", answer)
            yield {"event": "delta", "text": answer}
            yield {
                "event": "done",
                "answer": answer,
                "sources": relevant_docs,
                "language": language,
                "session_id": session_id,
            }
            return

        full_answer = ""
        sentence_buffer = ""
        sentence_count = 0

        try:
            stream = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a friendly student helper at UIT (Unitedworld Institute of Technology) - the engineering college at Karnavati University. You ONLY have information about UIT engineering programs (B.Tech in CSE, AIML, Data Science, Cyber Security, ECE). If asked about law, management, design, or other departments, politely clarify that you're specifically for UIT engineering and they should contact the main university office. Talk like a real person helping another student - natural, brief, and to the point. Give only key information they need in 2-4 sentences. No lists, no formal language, just helpful conversation. Use only the provided context."
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.5,
                max_tokens=250,
                top_p=0.9,
                stream=True,
            )

            sentence_pattern = re.compile(r"(.+?[.!?]+)(\s|$)", re.DOTALL)
            max_chunk_chars = 140

            for chunk in stream:
                token = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else ""
                if not token:
                    continue

                full_answer += token
                sentence_buffer += token
                yield {"event": "delta", "text": token}

                while True:
                    match = sentence_pattern.search(sentence_buffer)
                    if not match:
                        break
                    sentence = match.group(1).strip()
                    if sentence:
                        sentence_count += 1
                        yield {"event": "sentence", "text": sentence}
                    sentence_buffer = sentence_buffer[match.end():]

                # If punctuation hasn't arrived yet, flush a sentence-like chunk by length.
                if len(sentence_buffer) >= max_chunk_chars:
                    split_at = sentence_buffer.rfind(" ", 0, max_chunk_chars)
                    if split_at <= 0:
                        split_at = max_chunk_chars

                    chunk_text = sentence_buffer[:split_at].strip()
                    if chunk_text:
                        sentence_count += 1
                        yield {"event": "sentence", "text": chunk_text}
                    sentence_buffer = sentence_buffer[split_at:].lstrip()

            if sentence_buffer.strip():
                sentence_count += 1
                yield {"event": "sentence", "text": sentence_buffer.strip()}

            answer = full_answer.strip() if full_answer.strip() else self.generate_response(question, relevant_docs, language, history)

            self.memory.add_message(session_id, "user", question)
            self.memory.add_message(session_id, "assistant", answer)

            yield {
                "event": "done",
                "answer": answer,
                "sources": relevant_docs,
                "language": language,
                "session_id": session_id,
            }
            print(
                f"🌊 stream_query done | session={session_id} | chars={len(answer)} | "
                f"sentence_events={sentence_count} | duration_ms={int((time.perf_counter() - started_at) * 1000)}"
            )
        except Exception as e:
            print(
                f"❌ stream_query error | session={session_id} | duration_ms={int((time.perf_counter() - started_at) * 1000)} | error={e}"
            )
            yield {"event": "error", "message": str(e)}
    
    def clear_conversation(self, session_id: str = "default"):
        """Clear conversation history for a session"""
        self.memory.clear_session(session_id)
