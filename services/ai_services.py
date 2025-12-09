"""
AI Services (OOP Refactored)
Provides AI-powered insights using Google Gemini API with domain-specific assistants
"""

import os
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import streamlit as st


class AIAssistant(ABC):      # base class for all AI assistants; each domain gets its own assistant
    """
    Base class for AI-powered domain assistants.
    Each domain has a specialized assistant with custom prompts.
    """
    
    def __init__(self, domain_name: str):
        # initialize with domain name; used for logging and identification
        self.domain_name = domain_name
        self.model = None           # gemini model; created lazily when first used
        self._api_key = None        # api key cached after first retrieval
    
    @property
    def api_key(self) -> Optional[str]:
        """Get API key from multiple possible sources"""
        if self._api_key:
            return self._api_key        # return cached key if we already have it
        
        key = None      # will store the found api key
        
        # try to get from streamlit secrets first (for cloud deployment)
        try:
            key = st.secrets.get("GEMINI_API_KEY")
        except:
            pass        # secrets not available; not a problem for local dev
        
        # if not in secrets, try environment variables
        if not key:
            key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        self._api_key = key     # cache it for next time
        return key
    
    def initialize_model(self):
        """Initialize Gemini model; only runs once when first needed"""
        if self.model is not None:
            return      # already initialized; no need to do it again
        
        api_key = self.api_key
        if not api_key:
            raise ValueError(
                "⚠️ GEMINI_API_KEY not found. "
                "Set it in .env or .streamlit/secrets.toml"
            )
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)        # configure with our api key
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')      # use the latest flash model
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. "
                "Run: pip install google-generativeai"
            )
        except Exception as e:
            raise Exception(f"Failed to initialize Gemini model: {e}")
    
    @abstractmethod
    def build_prompt(self, record: Dict[str, Any]) -> str:
        """
        Build domain-specific prompt for AI analysis.
        Each child class implements its own prompt logic.
        """
        pass        # child classes must implement this
    
    def analyze(self, record: Dict[str, Any]) -> Optional[str]:
        """
        Analyze a record and return AI insights.
        This is the main method that gets called from the UI.
        """
        if not record:
            return "⚠️ No data provided for analysis"
        
        try:
            # make sure model is initialized
            self.initialize_model()
            
            # build domain-specific prompt
            prompt = self.build_prompt(record)
            
            # generate insights using gemini
            response = self.model.generate_content(prompt)
            return response.text if response else "❌ No response from AI"
        
        except ValueError as e:
            return str(e)       # api key error or configuration issue
        except ImportError as e:
            return str(e)       # missing library
        except Exception as e:
            return f"❌ Error generating insights: {str(e)}"
    
    def __str__(self):
        """String representation for user-friendly output"""
        return f"{self.__class__.__name__} for {self.domain_name}"
    
    def __repr__(self):
        """String representation for debugging"""
        return f"<{self.__class__.__name__}: {self.domain_name}>"


class CybersecurityAssistant(AIAssistant):      # ai assistant specialized for cybersecurity incidents
    """AI assistant for analyzing cybersecurity incidents"""
    
    def __init__(self):
        # initialize with cybersecurity domain
        super().__init__(domain_name="Cybersecurity")
    
    def build_prompt(self, incident: Dict[str, Any]) -> str:
        """Build prompt for cybersecurity incident analysis"""
        # extract incident details with defaults if missing
        category = incident.get('category', 'Unknown')
        severity = incident.get('severity', 'Unknown')
        status = incident.get('status', 'Unknown')
        description = incident.get('description', 'No description provided')
        
        # build comprehensive prompt for incident analysis
        prompt = f"""You are a cybersecurity analyst. Analyze this security incident:

**Incident Details:**
- Type: {category}
- Severity: {severity}
- Status: {status}
- Description: {description}

**Provide:**
1. **Immediate Impact**: What risks does this pose?
2. **Recommended Actions**: What should be done right now?
3. **Root Cause Analysis**: What likely caused this?
4. **Prevention**: How to prevent similar incidents?

Keep your analysis practical and actionable. Even if there is a lack of information, just assume in a generalized setting"""
        
        return prompt


class ITTicketAssistant(AIAssistant):      # ai assistant specialized for IT support tickets
    """AI assistant for troubleshooting IT tickets"""
    
    def __init__(self):
        # initialize with IT tickets domain
        super().__init__(domain_name="IT Tickets")
    
    def build_prompt(self, ticket: Dict[str, Any]) -> str:
        """Build prompt for IT ticket troubleshooting"""
        # extract ticket details
        title = ticket.get('title', 'Unknown')
        priority = ticket.get('priority', 'Unknown')
        status = ticket.get('status', 'Unknown')
        description = ticket.get('description', 'No description provided')
        
        # build troubleshooting prompt
        prompt = f"""You are an IT support specialist. Help with this ticket:

**Ticket Details:**
- Title: {title}
- Priority: {priority}
- Status: {status}
- Description: {description}

**Provide:**
1. **Diagnosis**: What's likely causing this issue?
2. **Quick Fixes**: Simple solutions to try first
3. **Detailed Solution**: Step-by-step resolution
4. **Prevention**: How to avoid this in future

Be clear and provide step-by-step instructions. Even if there is a lack of information, just assume in a generalized setting"""
        
        return prompt


class DatasetAssistant(AIAssistant):      # ai assistant specialized for dataset analysis
    """AI assistant for analyzing datasets"""
    
    def __init__(self):
        # initialize with datasets domain
        super().__init__(domain_name="Datasets")
    
    def build_prompt(self, dataset: Dict[str, Any]) -> str:
        """Build prompt for dataset analysis"""
        # extract dataset metadata
        name = dataset.get('name', 'Unknown')
        rows = dataset.get('rows', 0)
        columns = dataset.get('columns', 0)
        uploaded_by = dataset.get('uploaded_by', 'Unknown')
        
        # build analysis prompt
        prompt = f"""You are a data scientist. Analyze this dataset:

**Dataset Information:**
- Name: {name}
- Size: {rows} rows × {columns} columns
- Uploaded by: {uploaded_by}

**Provide:**
1. **Dataset Overview**: What kind of data is this likely to contain?
2. **Potential Insights**: What analyses would be valuable?
3. **Data Quality**: What to check for data quality?
4. **Visualization Ideas**: What charts/graphs would help?
5. **Business Value**: How can this data be used?

Focus on practical insights and actionable recommendations. Even if there is a lack of information, just assume in a generalized setting"""
        
        return prompt


# ==================== FACTORY FUNCTION ====================

def get_assistant_for_domain(domain: str) -> Optional[AIAssistant]:
    """
    Factory function to get the right AI assistant for a domain.
    Makes it easy to get the correct assistant without knowing class names.
    """
    # map domain names to assistant classes
    assistants = {
        "Cybersecurity": CybersecurityAssistant,
        "IT Tickets": ITTicketAssistant,
        "Datasets": DatasetAssistant
    }
    
    # get the assistant class and create instance
    assistant_class = assistants.get(domain)
    if assistant_class:
        return assistant_class()
    
    # domain not found
    print(f"Warning: No AI assistant found for domain '{domain}'")
    return None


# ==================== BACKWARD COMPATIBILITY ====================

def ai_insights_for(record: Dict[str, Any], domain: str) -> Optional[str]:
    """
    Legacy function for backward compatibility with old code.
    New code should use the assistant classes directly.
    """
    assistant = get_assistant_for_domain(domain)
    if assistant:
        return assistant.analyze(record)
    return f"⚠️ No AI assistant available for domain: {domain}"
