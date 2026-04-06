"""
Feedback Service for Voice RAG System
Manages user feedback on AI responses
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import uuid


class FeedbackService:
    """Service for managing user feedback"""
    
    def __init__(self, data_file: str = "feedback_data.json"):
        self.data_file = data_file
        self._ensure_data_file()
    
    def _ensure_data_file(self):
        """Create feedback data file if it doesn't exist"""
        if not os.path.exists(self.data_file):
            initial_data = {
                "feedback": [],
                "stats": {
                    "total_feedback": 0,
                    "positive": 0,
                    "negative": 0,
                    "satisfaction_rate": 0.0,
                    "by_language": {}
                }
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2)
    
    def _load_data(self) -> Dict:
        """Load feedback data from file"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_data(self, data: Dict):
        """Save feedback data to file"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def submit_feedback(
        self,
        message_id: str,
        rating: str,  # "positive" or "negative"
        query: str,
        response: str,
        language: str,
        session_id: Optional[str] = None,
        category: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Dict:
        """
        Submit user feedback
        
        Args:
            message_id: ID of the message being rated
            rating: "positive" or "negative"
            query: Original user question
            response: AI response
            language: Language of the conversation
            session_id: Optional session identifier
            category: Optional category for negative feedback
            comment: Optional text comment
        
        Returns:
            Feedback record with ID
        """
        data = self._load_data()
        
        # Create feedback record
        feedback_record = {
            "id": str(uuid.uuid4()),
            "message_id": message_id,
            "rating": rating,
            "query": query,
            "response": response,
            "language": language,
            "session_id": session_id or "anonymous",
            "category": category,
            "comment": comment,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to feedback list
        data["feedback"].append(feedback_record)
        
        # Update stats
        self._update_stats(data)
        
        # Save
        self._save_data(data)
        
        print(f"✅ Feedback recorded: {rating} for message {message_id}")
        
        return feedback_record
    
    def _update_stats(self, data: Dict):
        """Update statistics"""
        feedback_list = data["feedback"]
        total = len(feedback_list)
        
        if total == 0:
            return
        
        positive = sum(1 for f in feedback_list if f["rating"] == "positive")
        negative = total - positive
        
        # Overall stats
        data["stats"]["total_feedback"] = total
        data["stats"]["positive"] = positive
        data["stats"]["negative"] = negative
        data["stats"]["satisfaction_rate"] = round(positive / total * 100, 2) if total > 0 else 0.0
        
        # Stats by language
        by_language = {}
        for feedback in feedback_list:
            lang = feedback["language"]
            if lang not in by_language:
                by_language[lang] = {"total": 0, "positive": 0, "negative": 0}
            
            by_language[lang]["total"] += 1
            if feedback["rating"] == "positive":
                by_language[lang]["positive"] += 1
            else:
                by_language[lang]["negative"] += 1
        
        # Calculate satisfaction rate per language
        for lang, stats in by_language.items():
            stats["satisfaction_rate"] = round(
                stats["positive"] / stats["total"] * 100, 2
            ) if stats["total"] > 0 else 0.0
        
        data["stats"]["by_language"] = by_language
    
    def get_stats(self) -> Dict:
        """Get feedback statistics"""
        data = self._load_data()
        return data["stats"]
    
    def get_all_feedback(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all feedback records"""
        data = self._load_data()
        feedback = data["feedback"]
        
        # Sort by timestamp (newest first)
        feedback.sort(key=lambda x: x["timestamp"], reverse=True)
        
        if limit:
            return feedback[:limit]
        return feedback
    
    def get_negative_feedback(self) -> List[Dict]:
        """Get all negative feedback for review"""
        data = self._load_data()
        return [f for f in data["feedback"] if f["rating"] == "negative"]
    
    def export_feedback(self, output_file: str = "feedback_export.json"):
        """Export all feedback to a file"""
        data = self._load_data()
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return output_file


# Global feedback service instance
feedback_service = FeedbackService()
