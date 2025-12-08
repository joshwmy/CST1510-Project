"""
AI Services for generating insights using Google Gemini API
FIXED: Handles missing fields and matches actual database schema
"""
import google.generativeai as genai
import os
from typing import Dict, Any, Optional

def ai_insights_for(selected_incident: Dict[str, Any], domain: str = "Cybersecurity", **kwargs) -> Optional[str]:
    """
    Generate AI insights for an incident/ticket using Google Gemini API.
    
    Args:
        selected_incident: Dictionary containing incident/ticket data
        domain: The domain context (e.g., "Cybersecurity", "IT Tickets")
        **kwargs: Additional arguments (like button_key) that are ignored
    
    Returns:
        AI-generated insights as a string, or None if error occurs
    """
    try:
        # Get API key from environment
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return "⚠️ GEMINI_API_KEY not found in environment variables. Please set it to use AI insights."
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Initialize the model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Build the prompt based on domain and available fields
        if domain == "Cybersecurity":
            prompt = build_cybersecurity_prompt(selected_incident)
        elif domain == "IT Tickets":
            prompt = build_it_ticket_prompt(selected_incident)
        elif domain == "Datasets":
            prompt = build_dataset_prompt(selected_incident)
        else:
            prompt = build_generic_prompt(selected_incident, domain)
        
        # Generate content using Gemini
        response = model.generate_content(prompt)
        
        # Extract the response text
        if response and response.text:
            return response.text
        else:
            return "No insights generated."
            
    except Exception as e:
        return f"❌ Error generating AI insights: {str(e)}"


def build_cybersecurity_prompt(record: Dict[str, Any]) -> str:
    """
    Build a prompt for cybersecurity incident analysis.
    Matches cyber_incidents table schema:
    - id, incident_id, timestamp, severity, category, status, description, created_at
    """
    
    # Extract fields safely with defaults - matching actual schema
    db_id = record.get("id", "N/A")
    incident_id = record.get("incident_id", "N/A")
    timestamp = record.get("timestamp", "Unknown")
    severity = record.get("severity", "Unknown")
    category = record.get("category", "Unknown")
    status = record.get("status", "Unknown")
    description = record.get("description", "No description available")
    created_at = record.get("created_at", "Unknown")
    
    prompt = f"""You are a cybersecurity analyst assistant. Analyze the following security incident and provide actionable insights.

**Incident Details:**
- Incident ID: {incident_id}
- Timestamp: {timestamp}
- Severity: {severity}
- Category: {category}
- Status: {status}
- Database ID: {db_id}
- Recorded At: {created_at}

**Description:**
{description}

Please provide:
1. A brief analysis of the incident based on its category and severity
2. Potential root causes for this type of incident
3. Recommended immediate actions to address this {severity} severity issue
4. Prevention strategies to avoid similar {category} incidents in the future
5. Any relevant security best practices for this incident category

Keep your response concise, actionable, and focused on the specific incident details provided."""
    
    return prompt


def build_it_ticket_prompt(record: Dict[str, Any]) -> str:
    """
    Build a prompt for IT ticket analysis.
    Matches it_tickets table schema:
    - id, ticket_id, priority, description, status, assigned_to, created_at, resolution_time_hours, created_at_db
    """
    
    # Extract fields safely with defaults - matching actual schema
    db_id = record.get("id", "N/A")
    ticket_id = record.get("ticket_id", "N/A")
    priority = record.get("priority", "Unknown")
    description = record.get("description", "No description available")
    status = record.get("status", "Unknown")
    assigned_to = record.get("assigned_to", "Unassigned")
    created_at = record.get("created_at", "Unknown")
    resolution_time_hours = record.get("resolution_time_hours", "Not yet resolved")
    created_at_db = record.get("created_at_db", "Unknown")
    
    # Format resolution time nicely
    resolution_display = resolution_time_hours
    if resolution_time_hours and resolution_time_hours != "Not yet resolved":
        try:
            hours = int(resolution_time_hours)
            if hours < 24:
                resolution_display = f"{hours} hours"
            else:
                days = hours // 24
                remaining_hours = hours % 24
                resolution_display = f"{days} days, {remaining_hours} hours"
        except (ValueError, TypeError):
            resolution_display = str(resolution_time_hours)
    
    prompt = f"""You are an IT support assistant. Analyze the following support ticket and provide helpful guidance.

**Ticket Details:**
- Ticket ID: {ticket_id}
- Priority: {priority}
- Status: {status}
- Assigned To: {assigned_to}
- Created: {created_at}
- Resolution Time: {resolution_display}
- Database ID: {db_id}

**Description:**
{description}

Please provide:
1. Analysis of the issue based on the ticket description
2. Likely causes for this type of problem
3. Step-by-step troubleshooting recommendations
4. Estimated resolution time if not yet resolved (considering the {priority} priority)
5. Prevention tips to avoid similar issues in the future

Keep your response practical, user-friendly, and tailored to the {priority} priority level."""
    
    return prompt


def build_generic_prompt(record: Dict[str, Any], domain: str) -> str:
    """Build a generic prompt for any domain."""
    
    # Convert record to readable format
    record_text = "\n".join([f"- {key}: {value}" for key, value in record.items() if value is not None])
    
    prompt = f"""You are an expert analyst for {domain}. Analyze the following record and provide insights.

**Record Details:**
{record_text}

Please provide:
1. Key observations about this record
2. Analysis of the situation
3. Recommended actions based on the data
4. Best practices and prevention strategies

Keep your response clear, actionable, and relevant to the {domain} context."""
    
    return prompt


def build_dataset_prompt(record: Dict[str, Any]) -> str:
    """
    Build a prompt for dataset analysis.
    Matches datasets_metadata table schema:
    - id, dataset_id, name, rows, columns, uploaded_by, upload_date, created_at
    """
    
    # Extract fields safely with defaults - matching actual schema
    db_id = record.get("id", "N/A")
    dataset_id = record.get("dataset_id", "N/A")
    name = record.get("name", "Unnamed dataset")
    rows = record.get("rows", "Unknown")
    columns = record.get("columns", "Unknown")
    uploaded_by = record.get("uploaded_by", "Unknown")
    upload_date = record.get("upload_date", "Unknown")
    created_at = record.get("created_at", "Unknown")
    
    prompt = f"""You are a data analyst assistant. Analyze the following dataset metadata and provide insights.

**Dataset Details:**
- Dataset ID: {dataset_id}
- Name: {name}
- Dimensions: {rows} rows × {columns} columns
- Uploaded By: {uploaded_by}
- Upload Date: {upload_date}
- Database ID: {db_id}
- Recorded At: {created_at}

Please provide:
1. Analysis of the dataset size and structure
2. Potential use cases for this dataset based on its dimensions
3. Data quality considerations (what to check given the size)
4. Recommendations for data processing or analysis
5. Best practices for managing and utilizing this dataset

Keep your response practical and focused on actionable insights for working with this dataset."""
    
    return prompt


def get_field_safe(record: Dict[str, Any], *field_names: str, default: str = "N/A") -> str:
    """
    Safely get a field value from a record, trying multiple possible field names.
    
    Args:
        record: Dictionary containing the data
        *field_names: One or more field names to try (in order)
        default: Default value if none of the fields exist
    
    Returns:
        The first found value, or the default
    """
    for field_name in field_names:
        value = record.get(field_name)
        if value is not None:
            return str(value)
    return default