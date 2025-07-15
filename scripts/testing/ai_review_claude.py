"""
Claude-based code review script for Six Sigma quality validation.
"""
import os
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from anthropic import Anthropic


class ClaudeCodeReviewer:
    """Code reviewer using Claude for Six Sigma quality validation."""
    
    def __init__(self):
        """Initialize the Claude code reviewer."""
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = Anthropic(api_key=self.api_key)
        
        # Initialize output directory
        self.output_dir = Path('ai-reviews')
        self.output_dir.mkdir(exist_ok=True)
    
    def get_changed_files(self) -> List[Tuple[str, str]]:
        """Get list of changed files in the current PR."""
        # This is a simplified version. In practice, you'd use GitHub API
        changed_files = []
        for root, _, files in os.walk('src'):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        content = f.read()
                    changed_files.append((file_path, content))
        return changed_files
    
    def review_code(self, file_path: str, content: str) -> Dict:
        """Review code using Claude."""
        try:
            system_prompt = """
            You are a Six Sigma code reviewer. Analyze the code for:
            1. Code quality and best practices
            2. Potential bugs and security issues
            3. Performance optimizations
            4. Documentation completeness
            5. Test coverage requirements
            
            Provide a structured review with specific recommendations.
            """
            
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0.2,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": f"Review this code:\n\n{content}"
                }]
            )
            
            return {
                'file': file_path,
                'review': response.content[0].text,
                'status': 'success'
            }
        except Exception as e:
            return {
                'file': file_path,
                'review': f"Error during review: {str(e)}",
                'status': 'error'
            }
    
    def generate_metrics(self, reviews: List[Dict]) -> Dict:
        """Generate metrics from the reviews."""
        total_files = len(reviews)
        successful = sum(1 for r in reviews if r['status'] == 'success')
        success_rate = successful / total_files if total_files > 0 else 0
        
        return {
            'total_files_reviewed': total_files,
            'successful_reviews': successful,
            'success_rate': success_rate,
            'timestamp': str(datetime.datetime.now())
        }
    
    def run_review(self):
        """Run the complete review process."""
        print("Starting Claude code review...")
        
        # Get changed files
        changed_files = self.get_changed_files()
        
        # Review each file
        reviews = []
        for file_path, content in changed_files:
            print(f"Reviewing {file_path}...")
            review = self.review_code(file_path, content)
            reviews.append(review)
        
        # Generate metrics
        metrics = self.generate_metrics(reviews)
        
        # Save results
        output_file = self.output_dir / 'claude_review.json'
        with open(output_file, 'w') as f:
            json.dump({
                'reviews': reviews,
                'metrics': metrics
            }, f, indent=2)
        
        print("Claude code review completed.")
        
        # Exit with error if any reviews failed
        if any(r['status'] == 'error' for r in reviews):
            sys.exit(1)


if __name__ == '__main__':
    reviewer = ClaudeCodeReviewer()
    reviewer.run_review() 