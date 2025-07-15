from datetime import datetime, timedelta
import json
import math
import random
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union, Set

from fastapi import Depends, HTTPException, status
from sqlalchemy import and_, or_, func, desc, text
from sqlalchemy.orm import Session, joinedload

from app.core.logger import get_logger
from app.database import get_db

logger = get_logger(__name__)


class InsightType:
    """Types of local insights."""
    LOCAL_TIP = "local_tip"
    HIDDEN_GEM = "hidden_gem"
    BEST_TIME = "best_time"
    CROWD_ADVICE = "crowd_advice"
    LOCAL_FAVORITE = "local_favorite"
    INSIDER_SECRET = "insider_secret"
    AUTHENTIC_EXPERIENCE = "authentic_experience"
    PRACTICAL_ADVICE = "practical_advice"
    CULTURAL_CONTEXT = "cultural_context"
    HISTORICAL_CONTEXT = "historical_context"


class SourceType:
    """Types of insight sources."""
    LOCAL_BLOG = "local_blog"
    REVIEW = "review"
    SOCIAL_MEDIA = "social_media"
    TRAVEL_FORUM = "travel_forum"
    LOCAL_NEWS = "local_news"
    INTERVIEWS = "interviews"
    COMMUNITY_GROUPS = "community_groups"
    LOCAL_GUIDES = "local_guides"
    BUSINESS_OWNER = "business_owner"
    RESIDENT = "resident"


class LocalExpert:
    """
    Service for gathering and providing local expert knowledge and insights.
    
    This service aggregates information from various sources like local blogs,
    reviews, and community input to provide authentic, insider knowledge about
    locations and experiences that aren't typically found in standard travel guides.
    """
    
    def __init__(self, db: Session):
        """Initialize the local expert service with database session."""
        self.db = db
        self.nlp_models = {
            "sentiment": self._initialize_sentiment_analyzer(),
            "entity": self._initialize_entity_extractor(),
            "summarization": self._initialize_summarizer()
        }
        
        # Credibility weights for different source types
        self.source_credibility = {
            SourceType.LOCAL_BLOG: 0.85,
            SourceType.REVIEW: 0.70,
            SourceType.SOCIAL_MEDIA: 0.60,
            SourceType.TRAVEL_FORUM: 0.75,
            SourceType.LOCAL_NEWS: 0.80,
            SourceType.INTERVIEWS: 0.90,
            SourceType.COMMUNITY_GROUPS: 0.85,
            SourceType.LOCAL_GUIDES: 0.95,
            SourceType.BUSINESS_OWNER: 0.80,
            SourceType.RESIDENT: 0.90
        }
        
        # In a real implementation, insights would be stored in a database
        # Here we're using an in-memory store for demonstration
        self.insights_db = {}
    
    def _initialize_sentiment_analyzer(self):
        """Initialize the sentiment analysis model."""
        # In a real implementation, this would load a proper NLP model
        # For demonstration, we'll use a simple function
        return lambda text: {
            "score": random.uniform(-1, 1),
            "magnitude": random.uniform(0, 2),
            "positive": random.random() > 0.3,
            "confidence": random.uniform(0.6, 0.95)
        }
    
    def _initialize_entity_extractor(self):
        """Initialize the entity extraction model."""
        # In a real implementation, this would load a proper NLP model
        # For demonstration, we'll use a simple function
        def extract_entities(text):
            entities = []
            # Naive pattern matching for demonstration only
            if re.search(r"\b(park|trail|forest|garden|mountain)\b", text, re.IGNORECASE):
                entities.append({"type": "natural_feature", "confidence": random.uniform(0.7, 0.95)})
            if re.search(r"\b(museum|gallery|theater|cinema|concert)\b", text, re.IGNORECASE):
                entities.append({"type": "cultural_venue", "confidence": random.uniform(0.7, 0.95)})
            if re.search(r"\b(restaurant|cafe|bar|pub|eatery|diner)\b", text, re.IGNORECASE):
                entities.append({"type": "food_venue", "confidence": random.uniform(0.7, 0.95)})
            if re.search(r"\b(morning|afternoon|evening|night|dawn|dusk|early|late)\b", text, re.IGNORECASE):
                entities.append({"type": "time_reference", "confidence": random.uniform(0.7, 0.95)})
            if re.search(r"\b(avoid|skip|miss|crowd|busy|quiet|peaceful)\b", text, re.IGNORECASE):
                entities.append({"type": "advice", "confidence": random.uniform(0.7, 0.95)})
            return entities
        
        return extract_entities
    
    def _initialize_summarizer(self):
        """Initialize the text summarization model."""
        # In a real implementation, this would load a proper NLP model
        # For demonstration, we'll use a simple function
        def summarize(text, max_length=150):
            if len(text) <= max_length:
                return text
            # Naive summarization by truncation and adding ellipsis
            return text[:max_length - 3] + "..."
        
        return summarize
    
    async def analyze_reviews(
        self,
        reviews: List[Dict[str, Any]],
        location_name: str,
        location_type: str,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Analyze a collection of reviews to extract insights.
        
        Args:
            reviews: List of review dictionaries with text and metadata
            location_name: Name of the location being reviewed
            location_type: Type of location (restaurant, attraction, etc.)
            min_confidence: Minimum confidence threshold for insights
            
        Returns:
            List of insights extracted from reviews
        """
        try:
            insights = []
            
            for review in reviews:
                review_text = review.get("text", "")
                if not review_text or len(review_text) < 30:  # Skip very short reviews
                    continue
                
                # Analyze sentiment
                sentiment = self.nlp_models["sentiment"](review_text)
                
                # Extract entities
                entities = self.nlp_models["entity"](review_text)
                
                # Skip reviews with low confidence in all entities
                if not any(entity["confidence"] >= min_confidence for entity in entities):
                    continue
                
                # Generate insight based on content
                insight_type = self._determine_insight_type(entities, sentiment, review)
                
                if not insight_type:
                    continue
                
                # Extract the most relevant section of the review
                insight_text = self._extract_insight_text(review_text, entities, insight_type)
                
                # Determine credibility score
                credibility = self._calculate_credibility(review, insight_type)
                
                # Create insight object
                insight = {
                    "id": str(uuid.uuid4()),
                    "type": insight_type,
                    "text": insight_text,
                    "summary": self.nlp_models["summarization"](insight_text),
                    "source_type": SourceType.REVIEW,
                    "source_details": {
                        "reviewer_id": review.get("reviewer_id"),
                        "review_date": review.get("date"),
                        "rating": review.get("rating"),
                        "verified_visit": review.get("verified", False)
                    },
                    "location": {
                        "name": location_name,
                        "type": location_type
                    },
                    "sentiment": sentiment["score"],
                    "credibility_score": credibility,
                    "extracted_at": datetime.utcnow().isoformat(),
                    "entities": entities
                }
                
                insights.append(insight)
            
            # Sort by credibility
            insights.sort(key=lambda x: x["credibility_score"], reverse=True)
            
            return insights
        except Exception as e:
            logger.error(f"Error analyzing reviews: {str(e)}")
            return []
    
    def _determine_insight_type(
        self,
        entities: List[Dict[str, Any]],
        sentiment: Dict[str, Any],
        review: Dict[str, Any]
    ) -> Optional[str]:
        """
        Determine the type of insight based on content analysis.
        
        Args:
            entities: Extracted entities from text
            sentiment: Sentiment analysis results
            review: Original review data
            
        Returns:
            Insight type if identified, None otherwise
        """
        # Check for local tip patterns
        entity_types = [e["type"] for e in entities]
        review_text = review.get("text", "").lower()
        
        if "advice" in entity_types:
            if "time_reference" in entity_types:
                return InsightType.BEST_TIME
            elif re.search(r"\b(crowd|busy|quiet|avoid|skip)\b", review_text):
                return InsightType.CROWD_ADVICE
            else:
                return InsightType.PRACTICAL_ADVICE
        
        if re.search(r"\b(local|insider|secret|hidden|gem|favorite|best)\b", review_text):
            if "food_venue" in entity_types:
                return InsightType.LOCAL_FAVORITE
            elif re.search(r"\b(secret|hidden|gem)\b", review_text):
                return InsightType.HIDDEN_GEM
            elif re.search(r"\b(local|insider)\b", review_text):
                return InsightType.INSIDER_SECRET
            else:
                return InsightType.LOCAL_TIP
        
        if re.search(r"\b(authentic|real|genuine|tradition|cultural)\b", review_text):
            return InsightType.AUTHENTIC_EXPERIENCE
        
        if re.search(r"\b(history|historical|past|century|ancient|heritage)\b", review_text):
            return InsightType.HISTORICAL_CONTEXT
        
        if re.search(r"\b(culture|tradition|customs|locals|community)\b", review_text):
            return InsightType.CULTURAL_CONTEXT
        
        # Default insight type based on high rating and positive sentiment
        if review.get("rating", 0) >= 4 and sentiment["positive"]:
            return InsightType.LOCAL_TIP
        
        return None
    
    def _extract_insight_text(
        self,
        text: str,
        entities: List[Dict[str, Any]],
        insight_type: str
    ) -> str:
        """
        Extract the most relevant portion of text for the insight.
        
        Args:
            text: Full text to extract from
            entities: Extracted entities
            insight_type: Type of insight
            
        Returns:
            Most relevant text section
        """
        # In a real implementation, this would use more sophisticated NLP
        # to identify and extract the most relevant sentences
        
        # For demonstration, we'll use a simplified approach
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        if len(sentences) <= 3:
            return text
        
        # Score each sentence based on relevance to insight type
        scored_sentences = []
        for sentence in sentences:
            score = 0
            
            # Look for keywords related to the insight type
            if insight_type == InsightType.LOCAL_TIP and re.search(r"\b(tip|recommend|suggestion|advice)\b", sentence, re.IGNORECASE):
                score += 3
            elif insight_type == InsightType.HIDDEN_GEM and re.search(r"\b(hidden|gem|secret|discover|found)\b", sentence, re.IGNORECASE):
                score += 3
            elif insight_type == InsightType.BEST_TIME and re.search(r"\b(time|morning|afternoon|evening|night|hour|early|late)\b", sentence, re.IGNORECASE):
                score += 3
            elif insight_type == InsightType.CROWD_ADVICE and re.search(r"\b(crowd|busy|quiet|peak|avoid|wait)\b", sentence, re.IGNORECASE):
                score += 3
            elif insight_type == InsightType.LOCAL_FAVORITE and re.search(r"\b(local|favorite|popular|best|love)\b", sentence, re.IGNORECASE):
                score += 3
            elif insight_type == InsightType.INSIDER_SECRET and re.search(r"\b(insider|secret|know|trick|hack)\b", sentence, re.IGNORECASE):
                score += 3
            elif insight_type == InsightType.AUTHENTIC_EXPERIENCE and re.search(r"\b(authentic|genuine|real|tradition|experience)\b", sentence, re.IGNORECASE):
                score += 3
            elif insight_type == InsightType.PRACTICAL_ADVICE and re.search(r"\b(bring|wear|take|need|prepare|plan)\b", sentence, re.IGNORECASE):
                score += 3
            elif insight_type == InsightType.CULTURAL_CONTEXT and re.search(r"\b(culture|tradition|custom|history|heritage|local)\b", sentence, re.IGNORECASE):
                score += 3
            elif insight_type == InsightType.HISTORICAL_CONTEXT and re.search(r"\b(history|historical|century|year|past|built|founded)\b", sentence, re.IGNORECASE):
                score += 3
            
            # Check for entity mentions
            for entity in entities:
                entity_type = entity["type"]
                if (entity_type == "natural_feature" and re.search(r"\b(park|trail|forest|garden|mountain)\b", sentence, re.IGNORECASE)) or \
                   (entity_type == "cultural_venue" and re.search(r"\b(museum|gallery|theater|cinema|concert)\b", sentence, re.IGNORECASE)) or \
                   (entity_type == "food_venue" and re.search(r"\b(restaurant|cafe|bar|pub|eatery|diner)\b", sentence, re.IGNORECASE)):
                    score += 2
            
            scored_sentences.append((sentence, score))
        
        # Sort by score
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Take top 3 sentences
        top_sentences = [s[0] for s in scored_sentences[:3]]
        
        # Try to maintain original order
        ordered_top_sentences = [s for s in sentences if s in top_sentences]
        
        return " ".join(ordered_top_sentences)
    
    def _calculate_credibility(
        self,
        review: Dict[str, Any],
        insight_type: str
    ) -> float:
        """
        Calculate a credibility score for an insight.
        
        Args:
            review: Review data
            insight_type: Type of insight
            
        Returns:
            Credibility score between 0.0 and 1.0
        """
        base_score = 0.5
        
        # Verified reviews get a boost
        if review.get("verified", False):
            base_score += 0.2
        
        # High ratings get a boost for positive insights
        rating = review.get("rating", 0)
        if rating >= 4 and insight_type in [InsightType.LOCAL_FAVORITE, InsightType.HIDDEN_GEM, InsightType.AUTHENTIC_EXPERIENCE]:
            base_score += 0.15
        
        # Low ratings get a boost for practical advice and crowd tips
        if rating <= 3 and insight_type in [InsightType.PRACTICAL_ADVICE, InsightType.CROWD_ADVICE]:
            base_score += 0.1
        
        # Recent reviews get a boost
        review_date_str = review.get("date")
        if review_date_str:
            try:
                review_date = datetime.fromisoformat(review_date_str.replace("Z", "+00:00"))
                days_ago = (datetime.utcnow() - review_date).days
                if days_ago < 30:
                    base_score += 0.1
                elif days_ago < 90:
                    base_score += 0.05
                elif days_ago > 365:
                    base_score -= 0.1
            except:
                # If date parsing fails, don't adjust the score
                pass
        
        # Length of review can indicate detail
        text_length = len(review.get("text", ""))
        if text_length > 500:
            base_score += 0.1
        elif text_length < 100:
            base_score -= 0.1
        
        # Local reviewer gets a boost
        if review.get("is_local", False):
            base_score += 0.2
        
        # Cap at 0.0-1.0 range
        return max(0.0, min(1.0, base_score))
    
    async def process_blog_post(
        self,
        blog_post: Dict[str, Any],
        location_name: Optional[str] = None,
        location_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Process a local blog post to extract insights.
        
        Args:
            blog_post: Blog post data including text and metadata
            location_name: Optional specific location name
            location_type: Optional location type
            
        Returns:
            List of insights extracted from the blog post
        """
        try:
            insights = []
            
            # Extract the content sections
            content = blog_post.get("content", "")
            if not content or len(content) < 100:  # Skip very short posts
                return []
            
            # In a real implementation, we would use NLP to segment the content
            # into coherent sections. For demonstration, we'll split by paragraphs.
            sections = content.split("\n\n")
            
            for i, section in enumerate(sections):
                if len(section) < 50:  # Skip very short sections
                    continue
                
                # Analyze sentiment
                sentiment = self.nlp_models["sentiment"](section)
                
                # Extract entities
                entities = self.nlp_models["entity"](section)
                
                # Determine insight type
                insight_type = self._determine_insight_type_from_blog(section, entities, blog_post)
                
                if not insight_type:
                    continue
                
                # Determine location information
                section_location_name = location_name or blog_post.get("location_name")
                section_location_type = location_type or blog_post.get("location_type")
                
                # Create insight object
                insight = {
                    "id": str(uuid.uuid4()),
                    "type": insight_type,
                    "text": section,
                    "summary": self.nlp_models["summarization"](section),
                    "source_type": SourceType.LOCAL_BLOG,
                    "source_details": {
                        "blog_name": blog_post.get("blog_name"),
                        "author": blog_post.get("author"),
                        "publish_date": blog_post.get("publish_date"),
                        "url": blog_post.get("url")
                    },
                    "location": {
                        "name": section_location_name,
                        "type": section_location_type
                    },
                    "sentiment": sentiment["score"],
                    "credibility_score": self._calculate_blog_credibility(blog_post, insight_type),
                    "extracted_at": datetime.utcnow().isoformat(),
                    "entities": entities
                }
                
                insights.append(insight)
            
            # Sort by credibility
            insights.sort(key=lambda x: x["credibility_score"], reverse=True)
            
            return insights
        except Exception as e:
            logger.error(f"Error processing blog post: {str(e)}")
            return []
    
    def _determine_insight_type_from_blog(
        self,
        section: str,
        entities: List[Dict[str, Any]],
        blog_post: Dict[str, Any]
    ) -> Optional[str]:
        """
        Determine the type of insight from a blog post section.
        
        Args:
            section: Text section
            entities: Extracted entities
            blog_post: Original blog post data
            
        Returns:
            Insight type if identified, None otherwise
        """
        section_lower = section.lower()
        
        # Check for specific insight types based on content
        if re.search(r"\b(locals|insiders|only locals know|local favorite|where locals go)\b", section_lower):
            return InsightType.LOCAL_FAVORITE
        
        if re.search(r"\b(secret|hidden|gem|off the beaten path|undiscovered|overlooked)\b", section_lower):
            return InsightType.HIDDEN_GEM
        
        if re.search(r"\b(best time|visit during|morning|afternoon|evening|weekday|weekend|season|avoid)\b", section_lower) and \
           re.search(r"\b(crowd|busy|quiet|line|wait|peaceful|enjoy)\b", section_lower):
            return InsightType.BEST_TIME
        
        if re.search(r"\b(crowd|busy|quieter|peak hours|wait time|avoid|less crowded)\b", section_lower):
            return InsightType.CROWD_ADVICE
        
        if re.search(r"\b(tip|advice|recommend|suggestion|make sure|don't forget|remember to)\b", section_lower):
            return InsightType.LOCAL_TIP
        
        if re.search(r"\b(insider|secret|trick|hack|tip|local knowledge)\b", section_lower):
            return InsightType.INSIDER_SECRET
        
        if re.search(r"\b(authentic|genuine|real|tradition|experience|cultural|like a local)\b", section_lower):
            return InsightType.AUTHENTIC_EXPERIENCE
        
        if re.search(r"\b(bring|wear|take|need|prepare|plan|reserve|book|money|cash|card|hours|parking)\b", section_lower):
            return InsightType.PRACTICAL_ADVICE
        
        if re.search(r"\b(culture|tradition|custom|ritual|celebration|festival|meaning|significance)\b", section_lower):
            return InsightType.CULTURAL_CONTEXT
        
        if re.search(r"\b(history|historical|past|century|decade|year|ancient|heritage|built|founded|origin)\b", section_lower):
            return InsightType.HISTORICAL_CONTEXT
        
        # Check entities as a fallback
        entity_types = [e["type"] for e in entities]
        if "advice" in entity_types:
            return InsightType.PRACTICAL_ADVICE
        if "time_reference" in entity_types:
            return InsightType.BEST_TIME
        
        # If the blog is categorized, use that
        blog_category = blog_post.get("category", "").lower()
        if blog_category:
            if "history" in blog_category or "heritage" in blog_category:
                return InsightType.HISTORICAL_CONTEXT
            if "culture" in blog_category or "tradition" in blog_category:
                return InsightType.CULTURAL_CONTEXT
            if "food" in blog_category or "dining" in blog_category:
                return InsightType.LOCAL_FAVORITE
            if "tip" in blog_category or "advice" in blog_category:
                return InsightType.LOCAL_TIP
            if "secret" in blog_category or "hidden" in blog_category:
                return InsightType.HIDDEN_GEM
        
        return None
    
    def _calculate_blog_credibility(
        self,
        blog_post: Dict[str, Any],
        insight_type: str
    ) -> float:
        """
        Calculate credibility score for a blog post insight.
        
        Args:
            blog_post: Blog post data
            insight_type: Type of insight
            
        Returns:
            Credibility score between 0.0 and 1.0
        """
        # Start with base source credibility for blogs
        base_score = self.source_credibility.get(SourceType.LOCAL_BLOG, 0.7)
        
        # Local author gets a boost
        if blog_post.get("author_is_local", False):
            base_score += 0.15
        
        # Author expertise
        if blog_post.get("author_expertise", "").lower() in ["historian", "guide", "chef", "local expert"]:
            base_score += 0.1
        
        # Blog popularity and authority
        if blog_post.get("blog_authority_score", 0) > 7:
            base_score += 0.1
        
        # Recency
        publish_date_str = blog_post.get("publish_date")
        if publish_date_str:
            try:
                publish_date = datetime.fromisoformat(publish_date_str.replace("Z", "+00:00"))
                days_ago = (datetime.utcnow() - publish_date).days
                if days_ago < 30:
                    base_score += 0.1
                elif days_ago < 90:
                    base_score += 0.05
                elif days_ago > 365:
                    base_score -= 0.1
            except:
                # If date parsing fails, don't adjust the score
                pass
        
        # Content depth
        content_length = len(blog_post.get("content", ""))
        if content_length > 1000:
            base_score += 0.05
        
        # References and sources
        if blog_post.get("has_references", False):
            base_score += 0.1
        
        # Cap at 0.0-1.0 range
        return max(0.0, min(1.0, base_score))
    
    async def get_local_insights(
        self,
        latitude: float,
        longitude: float,
        location_name: Optional[str] = None,
        location_type: Optional[str] = None,
        insight_types: Optional[List[str]] = None,
        min_credibility: float = 0.6,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get relevant local insights for a location.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            location_name: Optional location name
            location_type: Optional location type
            insight_types: Optional list of specific insight types to include
            min_credibility: Minimum credibility score threshold
            limit: Maximum number of insights to return
            
        Returns:
            List of local insights for the location
        """
        try:
            # In a real implementation, this would query a database of
            # pre-processed insights near the given coordinates
            
            # For demonstration, we'll generate some sample insights
            all_insights = []
            
            # Simulate different source types
            source_types = [
                SourceType.LOCAL_BLOG,
                SourceType.REVIEW,
                SourceType.LOCAL_GUIDES,
                SourceType.RESIDENT
            ]
            
            # Simulate different insight types (use specified ones or all)
            available_insight_types = insight_types or [
                InsightType.LOCAL_TIP,
                InsightType.HIDDEN_GEM,
                InsightType.BEST_TIME,
                InsightType.CROWD_ADVICE,
                InsightType.LOCAL_FAVORITE,
                InsightType.INSIDER_SECRET,
                InsightType.AUTHENTIC_EXPERIENCE,
                InsightType.PRACTICAL_ADVICE
            ]
            
            # Generate sample insights
            for _ in range(10):  # Generate more than needed so we can filter
                source_type = random.choice(source_types)
                insight_type = random.choice(available_insight_types)
                
                # Generate sample text based on insight type
                text = self._generate_sample_insight_text(insight_type, location_name or "this place")
                
                # Calculate a random credibility score, weighted by source type
                base_cred = self.source_credibility.get(source_type, 0.5)
                credibility = base_cred * random.uniform(0.8, 1.1)
                
                # Ensure it meets minimum threshold
                if credibility < min_credibility:
                    continue
                
                # Create insight
                insight = {
                    "id": str(uuid.uuid4()),
                    "type": insight_type,
                    "text": text,
                    "summary": self.nlp_models["summarization"](text),
                    "source_type": source_type,
                    "source_details": self._generate_sample_source_details(source_type),
                    "location": {
                        "name": location_name or "Sample Location",
                        "type": location_type or "attraction",
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "sentiment": random.uniform(0.2, 0.9),  # Mostly positive
                    "credibility_score": credibility,
                    "extracted_at": datetime.utcnow().isoformat(),
                    "entities": []  # Simplified for demo
                }
                
                all_insights.append(insight)
            
            # Sort by credibility and take top results
            all_insights.sort(key=lambda x: x["credibility_score"], reverse=True)
            
            # Ensure diversity of insight types in results
            result_insights = []
            included_types = set()
            
            # First pass: take highest credibility of each type
            for insight in all_insights:
                if insight["type"] not in included_types and len(result_insights) < limit:
                    result_insights.append(insight)
                    included_types.add(insight["type"])
            
            # Second pass: fill remaining slots with highest credibility
            remaining_slots = limit - len(result_insights)
            if remaining_slots > 0:
                remaining_insights = [i for i in all_insights if i not in result_insights]
                result_insights.extend(remaining_insights[:remaining_slots])
            
            return result_insights
        except Exception as e:
            logger.error(f"Error getting local insights: {str(e)}")
            return []
    
    def _generate_sample_insight_text(self, insight_type: str, location_name: str) -> str:
        """Generate sample text for a given insight type (for demonstration only)."""
        if insight_type == InsightType.LOCAL_TIP:
            return f"When visiting {location_name}, make sure to check out the rooftop area - most tourists don't know it exists and it offers amazing views of the entire area."
        
        elif insight_type == InsightType.HIDDEN_GEM:
            return f"Skip the main entrance and head around to the north side of {location_name} where you'll find a small unmarked path. Follow it for about 5 minutes to discover a beautiful hidden garden that hardly anyone visits."
        
        elif insight_type == InsightType.BEST_TIME:
            return f"The best time to visit {location_name} is early morning before 9AM or after 4PM on weekdays. Weekends are extremely crowded, especially between 11AM and 2PM when tour buses arrive."
        
        elif insight_type == InsightType.CROWD_ADVICE:
            return f"To avoid the crowds at {location_name}, visit on Tuesday or Wednesday mornings. Most tourists come on weekends and Fridays, making it difficult to truly enjoy the experience."
        
        elif insight_type == InsightType.LOCAL_FAVORITE:
            return f"While tourists flock to the main attractions, locals prefer to visit the small shop behind {location_name} for the best authentic crafts at much better prices."
        
        elif insight_type == InsightType.INSIDER_SECRET:
            return f"A little-known secret about {location_name}: if you ask one of the staff about the 'special collection', they'll sometimes give you access to an incredible exhibition that's not advertised anywhere."
        
        elif insight_type == InsightType.AUTHENTIC_EXPERIENCE:
            return f"For a truly authentic experience at {location_name}, join the local cooking workshop that happens every Thursday evening. It's where residents gather to share traditional recipes handed down for generations."
        
        elif insight_type == InsightType.PRACTICAL_ADVICE:
            return f"Don't forget to bring cash when visiting {location_name}. Many of the best vendors don't accept credit cards, and the nearest ATM often has long lines."
        
        elif insight_type == InsightType.CULTURAL_CONTEXT:
            return f"The unique architecture of {location_name} reflects the cultural fusion that defined this region in the 18th century, blending Eastern influences with Western techniques in a way that tells the story of its people."
        
        elif insight_type == InsightType.HISTORICAL_CONTEXT:
            return f"{location_name} was originally built in 1782 as a trading post before being converted to its current use in the early 1900s. The east wing still has some of the original timber beams visible if you look up."
        
        else:
            return f"When visiting {location_name}, take some time to explore the surrounding area to discover some hidden treasures that most tourists miss."
    
    def _generate_sample_source_details(self, source_type: str) -> Dict[str, Any]:
        """Generate sample source details (for demonstration only)."""
        if source_type == SourceType.LOCAL_BLOG:
            return {
                "blog_name": "Authentic City Explorer",
                "author": "Local Guide Alice",
                "publish_date": (datetime.utcnow() - timedelta(days=random.randint(5, 120))).isoformat(),
                "url": "https://example.com/blog/authentic-experiences"
            }
        
        elif source_type == SourceType.REVIEW:
            return {
                "platform": "TripAdvisor",
                "reviewer_name": "Experienced Traveler",
                "review_date": (datetime.utcnow() - timedelta(days=random.randint(2, 90))).isoformat(),
                "rating": random.randint(4, 5),
                "verified_visit": True
            }
        
        elif source_type == SourceType.LOCAL_GUIDES:
            return {
                "guide_name": "City Secrets Tours",
                "experience_years": random.randint(5, 20),
                "local_residence_years": random.randint(10, 40),
                "specialization": random.choice(["History", "Food", "Culture", "Architecture"])
            }
        
        elif source_type == SourceType.RESIDENT:
            return {
                "residence_years": random.randint(10, 50),
                "neighborhood": "Historic District",
                "occupation": random.choice(["Teacher", "Chef", "Shopkeeper", "Artist", "Historian"]),
                "age_group": random.choice(["30-40", "40-50", "50-60", "60+"])
            }
        
        else:
            return {
                "source_name": "Local Knowledge Database",
                "reliability_score": random.uniform(0.7, 0.9),
                "last_updated": (datetime.utcnow() - timedelta(days=random.randint(1, 30))).isoformat()
            }
    
    async def get_expert_recommendations(
        self,
        latitude: float,
        longitude: float,
        category: str,
        user_preferences: Optional[Dict[str, Any]] = None,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get curated expert recommendations for a specific category.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            category: Recommendation category (food, activity, etc.)
            user_preferences: Optional user preferences
            limit: Maximum number of recommendations
            
        Returns:
            List of expert recommendations
        """
        try:
            # In a real implementation, this would query a database of
            # expert recommendations near the given coordinates
            
            # For demonstration, we'll generate sample recommendations
            recommendations = []
            
            # Get category-specific recommendations
            if category.lower() == "food":
                recommendations = self._generate_food_recommendations(latitude, longitude, user_preferences)
            elif category.lower() == "activity":
                recommendations = self._generate_activity_recommendations(latitude, longitude, user_preferences)
            elif category.lower() == "shopping":
                recommendations = self._generate_shopping_recommendations(latitude, longitude, user_preferences)
            elif category.lower() == "culture":
                recommendations = self._generate_culture_recommendations(latitude, longitude, user_preferences)
            else:
                recommendations = self._generate_general_recommendations(latitude, longitude, user_preferences)
            
            # Sort by expert score and take top results
            recommendations.sort(key=lambda x: x["expert_score"], reverse=True)
            
            return recommendations[:limit]
        except Exception as e:
            logger.error(f"Error getting expert recommendations: {str(e)}")
            return []
    
    def _generate_food_recommendations(
        self,
        latitude: float,
        longitude: float,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate sample food recommendations (for demonstration only)."""
        # Extract cuisine preferences if available
        cuisine_preferences = []
        if user_preferences and "cuisine" in user_preferences:
            cuisine_preferences = user_preferences["cuisine"]
        
        # Generate recommendations
        recommendations = []
        
        # Sample restaurant types
        restaurant_types = ["Local Gem", "Hidden Bistro", "Family-Run Eatery", "Authentic Tavern"]
        cuisines = cuisine_preferences or ["Local", "Italian", "Mediterranean", "Asian Fusion"]
        
        for i in range(5):
            restaurant_type = random.choice(restaurant_types)
            cuisine = random.choice(cuisines)
            
            recommendation = {
                "id": str(uuid.uuid4()),
                "name": f"{restaurant_type}: {cuisine} Delights",
                "category": "food",
                "subcategory": cuisine.lower(),
                "description": f"A wonderful {cuisine} restaurant loved by locals for its authentic flavors and charming atmosphere.",
                "expert_summary": f"This {restaurant_type.lower()} offers some of the most authentic {cuisine} food in the area, using traditional recipes and locally-sourced ingredients.",
                "highlights": [
                    "Family-owned for over 20 years",
                    "Uses locally-sourced ingredients",
                    f"Specializes in traditional {cuisine} dishes",
                    "Quiet atmosphere perfect for conversation"
                ],
                "must_try": [
                    f"House special {cuisine} platter",
                    "Seasonal menu items"
                ],
                "budget_category": random.choice(["$", "$$", "$$$"]),
                "best_times": ["Weekday evenings", "Sunday brunch"],
                "avoid_times": ["Friday and Saturday nights (very busy)"],
                "expert_score": random.uniform(0.8, 0.98),
                "local_popularity": random.uniform(0.75, 0.95),
                "tourist_rating": random.uniform(0.7, 0.9),
                "location": {
                    "latitude": latitude + random.uniform(-0.01, 0.01),
                    "longitude": longitude + random.uniform(-0.01, 0.01),
                    "address": "123 Local Street",
                    "neighborhood": "Historic District"
                },
                "expert": {
                    "name": "Chef Maria",
                    "credentials": "Local food critic and former chef",
                    "years_experience": random.randint(10, 25)
                }
            }
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _generate_activity_recommendations(
        self,
        latitude: float,
        longitude: float,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate sample activity recommendations (for demonstration only)."""
        # Extract activity preferences if available
        activity_preferences = []
        if user_preferences and "activities" in user_preferences:
            activity_preferences = user_preferences["activities"]
        
        # Generate recommendations
        recommendations = []
        
        # Sample activity types
        activity_types = ["Local Tour", "Outdoor Adventure", "Cultural Experience", "Workshops", "Nature Exploration"]
        themes = activity_preferences or ["Historical", "Adventure", "Cultural", "Nature", "Educational"]
        
        for i in range(5):
            activity_type = random.choice(activity_types)
            theme = random.choice(themes)
            
            recommendation = {
                "id": str(uuid.uuid4()),
                "name": f"{theme} {activity_type}",
                "category": "activity",
                "subcategory": theme.lower(),
                "description": f"An unforgettable {theme.lower()} experience that showcases the authentic local culture and landscapes.",
                "expert_summary": f"This {activity_type.lower()} offers a unique perspective on the area's {theme.lower()} aspects, curated by passionate locals with deep knowledge.",
                "highlights": [
                    "Small groups for personalized experience",
                    "Access to areas not in guidebooks",
                    "Led by local experts with cultural knowledge",
                    "Authentic interactions with residents"
                ],
                "best_for": [
                    "Curious travelers seeking deeper understanding",
                    "Those looking to escape tourist crowds",
                    "Photography enthusiasts"
                ],
                "duration": f"{random.randint(2, 5)} hours",
                "difficulty": random.choice(["Easy", "Moderate", "Challenging"]),
                "expert_score": random.uniform(0.8, 0.98),
                "local_popularity": random.uniform(0.75, 0.95),
                "tourist_rating": random.uniform(0.7, 0.9),
                "location": {
                    "latitude": latitude + random.uniform(-0.01, 0.01),
                    "longitude": longitude + random.uniform(-0.01, 0.01),
                    "meeting_point": "Central Plaza",
                    "area_covered": "Historic District and surroundings"
                },
                "expert": {
                    "name": "Local Guide James",
                    "credentials": f"Lifetime resident and {theme.lower()} specialist",
                    "years_experience": random.randint(5, 30)
                }
            }
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _generate_shopping_recommendations(
        self,
        latitude: float,
        longitude: float,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate sample shopping recommendations (for demonstration only)."""
        # Generate recommendations
        recommendations = []
        
        # Sample shop types
        shop_types = ["Artisan Workshop", "Local Market", "Boutique Store", "Craft Shop", "Vintage Emporium"]
        product_types = ["Handcrafts", "Local Specialties", "Artisanal Foods", "Unique Souvenirs", "Traditional Crafts"]
        
        for i in range(5):
            shop_type = random.choice(shop_types)
            product_type = random.choice(product_types)
            
            recommendation = {
                "id": str(uuid.uuid4()),
                "name": f"{shop_type}: {product_type}",
                "category": "shopping",
                "subcategory": product_type.lower().replace(" ", "_"),
                "description": f"A wonderful place to find authentic {product_type.lower()} made by local artisans.",
                "expert_summary": f"This {shop_type.lower()} offers a curated selection of {product_type.lower()} that you won't find in typical tourist shops, with items created by local craftspeople.",
                "highlights": [
                    "Direct from local artisans",
                    "Traditional techniques and materials",
                    "Unique items not available elsewhere",
                    "Fair prices that support the local community"
                ],
                "must_buy": [
                    f"Signature {product_type.lower()}",
                    "Limited edition seasonal items"
                ],
                "price_range": random.choice(["Budget-friendly", "Mid-range", "High-end"]),
                "bargaining": random.choice(["Expected", "Acceptable for large purchases", "Fixed prices"]),
                "expert_score": random.uniform(0.8, 0.98),
                "local_popularity": random.uniform(0.75, 0.95),
                "tourist_rating": random.uniform(0.7, 0.9),
                "location": {
                    "latitude": latitude + random.uniform(-0.01, 0.01),
                    "longitude": longitude + random.uniform(-0.01, 0.01),
                    "address": "45 Artisan Lane",
                    "neighborhood": "Old Quarter"
                },
                "expert": {
                    "name": "Craft Expert Sarah",
                    "credentials": "Local artisan and shopping guide",
                    "years_experience": random.randint(7, 20)
                }
            }
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _generate_culture_recommendations(
        self,
        latitude: float,
        longitude: float,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate sample cultural recommendations (for demonstration only)."""
        # Generate recommendations
        recommendations = []
        
        # Sample cultural venue types
        venue_types = ["Hidden Museum", "Local Cultural Center", "Historic Site", "Cultural Workshop", "Community Theater"]
        themes = ["Heritage", "Traditional Arts", "Local History", "Folk Culture", "Contemporary Arts"]
        
        for i in range(5):
            venue_type = random.choice(venue_types)
            theme = random.choice(themes)
            
            recommendation = {
                "id": str(uuid.uuid4()),
                "name": f"{venue_type}: {theme} Experience",
                "category": "culture",
                "subcategory": theme.lower().replace(" ", "_"),
                "description": f"An enriching cultural venue showcasing the region's {theme.lower()} in an intimate setting.",
                "expert_summary": f"This {venue_type.lower()} offers an authentic glimpse into local {theme.lower()}, curated by community members rather than commercial interests.",
                "highlights": [
                    "Authentic cultural programming",
                    "Operated by local cultural preservation society",
                    "Interactive exhibits and demonstrations",
                    "Personal stories from community members"
                ],
                "special_experiences": [
                    "Guided tours by community elders",
                    f"Weekly {theme.lower()} workshops",
                    "Cultural performances on weekends"
                ],
                "ideal_visit_length": f"{random.randint(1, 3)} hours",
                "best_days": random.choice(["Weekdays", "Weekends", "Thursday evenings (special programming)"]),
                "expert_score": random.uniform(0.8, 0.98),
                "local_significance": random.uniform(0.8, 1.0),
                "tourist_awareness": random.uniform(0.2, 0.7),
                "location": {
                    "latitude": latitude + random.uniform(-0.01, 0.01),
                    "longitude": longitude + random.uniform(-0.01, 0.01),
                    "address": "78 Heritage Street",
                    "neighborhood": "Cultural District"
                },
                "expert": {
                    "name": "Cultural Historian Elena",
                    "credentials": f"Director of Local {theme} Studies",
                    "years_experience": random.randint(10, 35)
                }
            }
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _generate_general_recommendations(
        self,
        latitude: float,
        longitude: float,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate general recommendations (for demonstration only)."""
        # Mix of different recommendation types
        recommendations = []
        recommendations.extend(self._generate_food_recommendations(latitude, longitude, user_preferences)[:2])
        recommendations.extend(self._generate_activity_recommendations(latitude, longitude, user_preferences)[:2])
        recommendations.extend(self._generate_culture_recommendations(latitude, longitude, user_preferences)[:1])
        
        return recommendations


def get_local_expert(db: Session = Depends(get_db)) -> LocalExpert:
    """
    Dependency to get the local expert service.
    
    Args:
        db: Database session dependency
        
    Returns:
        LocalExpert instance
    """
    return LocalExpert(db)