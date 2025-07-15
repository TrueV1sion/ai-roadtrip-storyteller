"""
Compare and analyze code reviews from multiple AI models.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from difflib import SequenceMatcher


def load_reviews(review_dir: Path) -> Tuple[Dict, Dict]:
    """Load review results from both AI models."""
    try:
        with open(review_dir / 'gpt4_review.json', 'r') as f:
            gpt4_data = json.load(f)
        with open(review_dir / 'claude_review.json', 'r') as f:
            claude_data = json.load(f)
        return gpt4_data, claude_data
    except FileNotFoundError as e:
        print(f"Error loading review files: {e}")
        sys.exit(1)


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two text strings."""
    return SequenceMatcher(None, text1, text2).ratio()


def analyze_reviews(
    gpt4_data: Dict,
    claude_data: Dict
) -> Tuple[List[Dict], Dict]:
    """Analyze and compare reviews from both models."""
    comparison_results = []
    
    # Match reviews by file
    gpt4_reviews = {r['file']: r for r in gpt4_data['reviews']}
    claude_reviews = {r['file']: r for r in claude_data['reviews']}
    
    all_files = set(gpt4_reviews.keys()) | set(claude_reviews.keys())
    
    for file in all_files:
        gpt4_review = gpt4_reviews.get(file, {'status': 'missing'})
        claude_review = claude_reviews.get(file, {'status': 'missing'})
        
        success = (
            gpt4_review['status'] == 'success' and 
            claude_review['status'] == 'success'
        )
        
        if success:
            similarity = calculate_similarity(
                gpt4_review['review'],
                claude_review['review']
            )
        else:
            similarity = 0.0
        
        comparison_results.append({
            'file': file,
            'gpt4_status': gpt4_review['status'],
            'claude_status': claude_review['status'],
            'similarity_ratio': similarity,
            'consensus': similarity > 0.7
        })
    
    # Calculate aggregate metrics
    total_similarity = sum(
        r['similarity_ratio'] 
        for r in comparison_results
    )
    avg_similarity = total_similarity / len(comparison_results)
    
    metrics = {
        'total_files': len(all_files),
        'consensus_count': sum(
            1 for r in comparison_results if r['consensus']
        ),
        'average_similarity': avg_similarity,
        'gpt4_success_rate': gpt4_data['metrics']['success_rate'],
        'claude_success_rate': claude_data['metrics']['success_rate']
    }
    
    return comparison_results, metrics


def save_comparison(
    results: List[Dict],
    metrics: Dict,
    output_dir: Path
) -> None:
    """Save comparison results to file."""
    output_file = output_dir / 'comparison_results.json'
    with open(output_file, 'w') as f:
        json.dump({
            'comparisons': results,
            'metrics': metrics
        }, f, indent=2)


def main():
    """Main function to run the comparison."""
    review_dir = Path('ai-reviews')
    if not review_dir.exists():
        print("AI reviews directory not found")
        sys.exit(1)
    
    print("Loading AI review results...")
    gpt4_data, claude_data = load_reviews(review_dir)
    
    print("Analyzing reviews...")
    results, metrics = analyze_reviews(gpt4_data, claude_data)
    
    print("Saving comparison results...")
    save_comparison(results, metrics, review_dir)
    
    # Print summary
    print("\nComparison Summary:")
    print(f"Total files reviewed: {metrics['total_files']}")
    print(
        f"Files with consensus: "
        f"{metrics['consensus_count']} "
        f"({metrics['consensus_count']/metrics['total_files']*100:.1f}%)"
    )
    print(f"Average similarity: {metrics['average_similarity']*100:.1f}%")
    print(
        f"GPT-4 success rate: {metrics['gpt4_success_rate']*100:.1f}%"
    )
    print(
        f"Claude success rate: {metrics['claude_success_rate']*100:.1f}%"
    )
    
    # Exit with error if consensus is too low
    consensus_ratio = metrics['consensus_count'] / metrics['total_files']
    if consensus_ratio < 0.7:
        print("\nWARNING: Low consensus between AI models")
        sys.exit(1)


if __name__ == '__main__':
    main() 