"""Utilities for extraction result handling and normalization.

This module provides helper functions for working with extraction results
that may be in legacy format (Optional[str]) or modern format (tuple[Optional[str], dict]).
"""

from typing import Optional, Union, Dict, Any, Tuple


def normalize_extraction_result(
    result: Union[Optional[str], Tuple[Optional[str], Dict[str, Any]]]
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Normalize extraction result to consistent format.

    Handles both legacy (Optional[str]) and modern (tuple) return types from extractors,
    converting them to a consistent tuple format for unified handling.

    Args:
        result: Extraction result in either format:
            - Optional[str]: Legacy format (just the text)
            - tuple[Optional[str], dict]: Modern format (text + metadata)

    Returns:
        tuple[Optional[str], dict]: Normalized result as (text, metadata)
            - text: Extracted text or None
            - metadata: Extraction metadata dict (empty if legacy format)

    Examples:
        >>> # Legacy format
        >>> text, metadata = normalize_extraction_result("ingredients text")
        >>> print(text, metadata)
        'ingredients text' {}

        >>> # Modern format
        >>> text, metadata = normalize_extraction_result(("ingredients", {"confidence": 0.9}))
        >>> print(text, metadata)
        'ingredients' {'confidence': 0.9}

        >>> # None result
        >>> text, metadata = normalize_extraction_result(None)
        >>> print(text, metadata)
        None {}
    """
    if result is None:
        # None result - no extraction
        return None, {}
    elif isinstance(result, tuple):
        # Modern format: (text, metadata)
        if len(result) == 2:
            text, metadata = result
            # Ensure metadata is a dict
            if not isinstance(metadata, dict):
                return text, {}
            return text, metadata
        else:
            # Invalid tuple format - treat as legacy
            return result, {}
    elif isinstance(result, str):
        # Legacy format: just the text
        return result, {}
    else:
        # Unknown format - return as-is with empty metadata
        return result, {}


def merge_extraction_metadata(
    base_metadata: Dict[str, Any],
    extraction_metadata: Dict[str, Any],
    component_name: str
) -> Dict[str, Any]:
    """Merge extraction metadata into recipe metadata under a component key.

    Args:
        base_metadata: Base recipe metadata dictionary
        extraction_metadata: Extraction metadata from normalize_extraction_result()
        component_name: Component name (e.g., 'ingredients', 'instructions')

    Returns:
        Updated metadata dictionary with extraction data under 'extraction' key

    Examples:
        >>> base = {}
        >>> extraction = {"confidence": 0.9, "strategy": "pattern"}
        >>> result = merge_extraction_metadata(base, extraction, "ingredients")
        >>> print(result)
        {'extraction': {'ingredients': {'confidence': 0.9, 'strategy': 'pattern'}}}
    """
    if not extraction_metadata:
        # No metadata to merge
        return base_metadata

    # Create extraction section if it doesn't exist
    if "extraction" not in base_metadata:
        base_metadata["extraction"] = {}

    # Store component-specific metadata
    base_metadata["extraction"][component_name] = extraction_metadata

    return base_metadata


def get_extraction_confidence(
    recipe_metadata: Dict[str, Any],
    component_name: str
) -> Optional[float]:
    """Get extraction confidence score for a specific component.

    Args:
        recipe_metadata: Recipe metadata dictionary
        component_name: Component name (e.g., 'ingredients', 'instructions')

    Returns:
        Confidence score (0.0-1.0) or None if not available

    Examples:
        >>> metadata = {'extraction': {'ingredients': {'confidence': 0.85}}}
        >>> get_extraction_confidence(metadata, 'ingredients')
        0.85
    """
    try:
        result = recipe_metadata.get("extraction", {}).get(component_name, {}).get("confidence")
        return float(result) if result is not None else None
    except (AttributeError, KeyError):
        return None


def get_extraction_strategy(
    recipe_metadata: Dict[str, Any],
    component_name: str
) -> Optional[str]:
    """Get extraction strategy used for a specific component.

    Args:
        recipe_metadata: Recipe metadata dictionary
        component_name: Component name (e.g., 'ingredients', 'instructions')

    Returns:
        Strategy name or None if not available

    Examples:
        >>> metadata = {'extraction': {'ingredients': {'strategy': 'structural_zones'}}}
        >>> get_extraction_strategy(metadata, 'ingredients')
        'structural_zones'
    """
    try:
        result = recipe_metadata.get("extraction", {}).get(component_name, {}).get("strategy")
        return str(result) if result is not None else None
    except (AttributeError, KeyError):
        return None
