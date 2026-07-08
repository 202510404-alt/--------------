from typing import List

def calculate_cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    """
    외부 Vector DB 없이 순수 파이썬 또는 NumPy를 활용하여 
    두 벡터 간의 코사인 유사도(Cosine Similarity)를 수학적으로 계산합니다.
    
    Args:
        vector_a (List[float]): 기준 벡터 (Query Embedding).
        vector_b (List[float]): 비교 대상 벡터 (Page Embedding).
        
    Returns:
        float: -1.0에서 1.0 사이의 코사인 유사도 실수 값.
    """
    pass