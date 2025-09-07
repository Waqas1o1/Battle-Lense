import json
from datetime import datetime
from pathlib import Path

async def generate_report(session, final_result, user_input):
    """Generate a comprehensive report of the analysis"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get conversation history from session if available
    conversation_data = []
    try:
        # Assuming session has a method to get conversation history
        if hasattr(session, 'get_conversation_history'):
            conversation_data = session.get_conversation_history()
        elif hasattr(session, 'messages'):
            conversation_data = session.messages
    except:
        pass
    
    report = {
        "metadata": {
            "timestamp": timestamp,
            "user_query": user_input,
            "report_type": "Country Comparison Analysis"
        },
        "analysis_result": final_result,
        "conversation_history": conversation_data,
        "summary": {
            "generated_at": timestamp,
            "total_interactions": len(conversation_data) if conversation_data else 0
        }
    }
    
    return report

def save_report(report, filename=None):
    """Save report to file in multiple formats"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"country_comparison_report_{timestamp}"
    
    # Create reports directory if it doesn't exist
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Save as JSON
    json_file = reports_dir / f"{filename}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Save as readable text report
    txt_file = reports_dir / f"{filename}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("COUNTRY COMPARISON ANALYSIS REPORT\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"Generated: {report['metadata']['timestamp']}\n")
        f.write(f"User Query: {report['metadata']['user_query']}\n\n")
        
        f.write("ANALYSIS RESULT:\n")
        f.write("-" * 30 + "\n")
        f.write(f"{report['analysis_result']}\n\n")
        
        if report['conversation_history']:
            f.write("CONVERSATION HISTORY:\n")
            f.write("-" * 30 + "\n")
            for i, interaction in enumerate(report['conversation_history'], 1):
                f.write(f"{i}. {interaction}\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("End of Report\n")
    
    return json_file, txt_file
