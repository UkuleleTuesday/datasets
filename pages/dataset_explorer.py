import json
import pandas as pd
import streamlit as st
import urllib.request
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from jsonschema import validate, ValidationError


@st.cache_data
def discover_datasets() -> Dict[str, Dict[str, Any]]:
    """Auto-discover available datasets by scanning the schemas directory."""
    schemas_dir = Path(__file__).parent.parent / "schemas"
    datasets = {}
    
    if not schemas_dir.exists():
        return datasets
    
    # Look for JSON schema files
    for schema_file in schemas_dir.glob("*.json"):
        if schema_file.name == "README.md":
            continue
            
        dataset_name = schema_file.stem
        # Convert schema filename to dataset type
        if dataset_name == "sessions":
            dataset_type = "jam-sessions"
        elif dataset_name == "song-sheets":
            dataset_type = "song-sheets"
        else:
            dataset_type = dataset_name
            
        try:
            with open(schema_file, 'r') as f:
                schema = json.load(f)
            
            datasets[dataset_type] = {
                "name": dataset_name.replace("-", " ").title(),
                "schema_file": str(schema_file),
                "schema": schema,
                "description": schema.get("description", schema.get("title", "No description available"))
            }
        except (json.JSONDecodeError, FileNotFoundError) as e:
            st.warning(f"Could not load schema for {dataset_name}: {e}")
    
    return datasets


def extract_schema_info(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Extract useful information from a JSON schema for UI generation."""
    info = {
        "title": schema.get("title", "Unknown Dataset"),
        "description": schema.get("description", "No description available"),
        "type": schema.get("type", "object"),
        "fields": {}
    }
    
    # Handle array schemas (like song-sheets)
    if schema.get("type") == "array" and "items" in schema:
        items_schema = schema["items"]
        if "properties" in items_schema:
            # Extract top-level properties first
            info["fields"] = extract_properties(items_schema["properties"])
            
            # Handle nested properties (like song-sheets with properties.properties)
            props = items_schema.get("properties", {})
            for prop_name, prop_schema in props.items():
                if prop_name == "properties" and "properties" in prop_schema:
                    # Extract nested properties and add them with prefix
                    nested_props = extract_properties(prop_schema["properties"])
                    info["fields"].update({f"properties.{k}": v for k, v in nested_props.items()})
    
    # Handle object schemas (like sessions)
    elif schema.get("type") == "object" and "properties" in schema:
        info["fields"] = extract_properties(schema["properties"])
    
    return info


def extract_properties(properties: Dict[str, Any]) -> Dict[str, Any]:
    """Extract field information from schema properties."""
    fields = {}
    for field_name, field_schema in properties.items():
        fields[field_name] = extract_field_info(field_schema)
    return fields


def extract_field_info(field_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Extract information about a single field from its schema."""
    field_info = {
        "type": field_schema.get("type", "unknown"),
        "description": field_schema.get("description", ""),
        "required": False,  # Will be set by calling function
        "enum": field_schema.get("enum"),
        "pattern": field_schema.get("pattern"),
        "format": field_schema.get("format"),
        "minimum": field_schema.get("minimum"),
        "maximum": field_schema.get("maximum")
    }
    
    # Handle array types
    if isinstance(field_info["type"], list):
        field_info["type"] = " | ".join(str(t) for t in field_info["type"])
    
    return field_info


@st.cache_data(ttl=600)
def load_data_from_public_url(dataset_type: str) -> Optional[pd.DataFrame]:
    """Load dataset data from public GCS URL."""
    # Map dataset types to their public URLs
    dataset_urls = {
        "song-sheets": "https://ukulele-tuesday-datasets.storage.googleapis.com/song-sheets/aggregated/latest/data.jsonl",
        "jam-sessions": "https://ukulele-tuesday-datasets.storage.googleapis.com/jam-sessions/latest/data.jsonl"
    }
    
    if dataset_type not in dataset_urls:
        return None
    
    dataset_url = dataset_urls[dataset_type]
    all_data = []

    try:
        with st.spinner(f"Loading {dataset_type} dataset from public URL..."):
            with urllib.request.urlopen(dataset_url) as response:
                if response.status != 200:
                    st.error(f"Failed to fetch data: HTTP {response.status}")
                    return None
                for line in response:
                    try:
                        all_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        st.warning(f"Skipping invalid JSON line in {dataset_type} dataset")
                        continue

        if not all_data:
            st.error(f"No data found in the {dataset_type} dataset file.")
            return None

        df = pd.json_normalize(all_data)
        st.success(f"Successfully loaded {len(all_data)} {dataset_type} records from public dataset")
        return df

    except Exception as e:
        st.error(f"Error loading {dataset_type} data from public URL: {e}")
        return None


@st.cache_data
def load_dataset_data(dataset_type: str) -> Optional[pd.DataFrame]:
    """Load dataset data from public GCS URL."""
    return load_data_from_public_url(dataset_type)



def format_field_value(value: Any, field_info: Dict[str, Any]) -> str:
    """Format a field value according to its schema information."""
    # Handle arrays/lists first
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return "[]"
        elif len(value) <= 3:
            return f"[{', '.join(str(item) for item in value)}]"
        else:
            return f"[{', '.join(str(item) for item in value[:3])}, ... ({len(value)} items)]"
    
    # Handle None/NaN values
    try:
        if pd.isna(value) or value is None:
            return "N/A"
    except (ValueError, TypeError):
        # pd.isna can fail on complex objects, just check for None
        if value is None:
            return "N/A"
    
    field_type = field_info.get("type", "")
    field_format = field_info.get("format")
    
    # Handle different data types
    if "date" in field_type or field_format == "date":
        try:
            if isinstance(value, str) and len(value) == 8 and value.isdigit():
                # YYYYMMDD format
                return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
            return pd.to_datetime(value).strftime("%Y-%m-%d")
        except:
            return str(value)
    elif "number" in field_type or "integer" in field_type:
        try:
            return f"{float(value):.2f}" if "." in str(value) else str(int(float(value)))
        except:
            return str(value)
    else:
        return str(value)


def create_data_filters(df: pd.DataFrame, schema_info: Dict[str, Any]) -> Dict[str, Any]:
    """Create filter widgets based on schema information."""
    filters = {}
    
    # Create filter widgets in sidebar
    st.sidebar.header("Filters")
    
    for field_name, field_info in schema_info["fields"].items():
        if field_name not in df.columns:
            continue
            
        field_type = field_info.get("type", "")
        enum_values = field_info.get("enum")
        
        # Skip fields with too many unique values for filtering
        try:
            unique_count = df[field_name].nunique()
        except (TypeError, ValueError):
            # Skip fields that contain unhashable types (like lists)
            continue
            
        if unique_count > 50 and not enum_values:
            continue
        
        if enum_values:
            # Dropdown for enum values
            selected = st.sidebar.multiselect(
                f"Filter {field_name}",
                options=enum_values,
                key=f"filter_{field_name}"
            )
            if selected:
                filters[field_name] = selected
        elif "string" in field_type and unique_count <= 20:
            # Multiselect for string fields with few values
            options = df[field_name].dropna().unique().tolist()
            selected = st.sidebar.multiselect(
                f"Filter {field_name}",
                options=sorted(options),
                key=f"filter_{field_name}"
            )
            if selected:
                filters[field_name] = selected
        elif "number" in field_type or "integer" in field_type:
            # Range slider for numeric fields
            min_val = df[field_name].min()
            max_val = df[field_name].max()
            if pd.notna(min_val) and pd.notna(max_val) and min_val != max_val:
                selected_range = st.sidebar.slider(
                    f"Filter {field_name}",
                    min_value=float(min_val),
                    max_value=float(max_val),
                    value=(float(min_val), float(max_val)),
                    key=f"filter_{field_name}"
                )
                if selected_range != (float(min_val), float(max_val)):
                    filters[field_name] = selected_range
    
    return filters


def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """Apply filters to the dataframe."""
    filtered_df = df.copy()
    
    for field_name, filter_value in filters.items():
        if field_name not in filtered_df.columns:
            continue
            
        if isinstance(filter_value, list):
            # Multiple selection filter
            filtered_df = filtered_df[filtered_df[field_name].isin(filter_value)]
        elif isinstance(filter_value, tuple) and len(filter_value) == 2:
            # Range filter
            min_val, max_val = filter_value
            filtered_df = filtered_df[
                (filtered_df[field_name] >= min_val) & 
                (filtered_df[field_name] <= max_val)
            ]
    
    return filtered_df


def display_data_table(df: pd.DataFrame, schema_info: Dict[str, Any]):
    """Display the data table with pagination and formatting."""
    if df.empty:
        st.warning("No data available after applying filters.")
        return
    
    # Pagination
    items_per_page = st.selectbox("Items per page", [10, 25, 50, 100], index=1)
    total_pages = (len(df) - 1) // items_per_page + 1
    
    if total_pages > 1:
        page = st.selectbox("Page", range(1, total_pages + 1))
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_df = df.iloc[start_idx:end_idx]
    else:
        page_df = df
    
    # Format data according to schema
    display_df = page_df.copy()
    for field_name, field_info in schema_info["fields"].items():
        if field_name in display_df.columns:
            display_df[field_name] = display_df[field_name].apply(
                lambda x: format_field_value(x, field_info)
            )
    
    # Display table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Show pagination info
    if total_pages > 1:
        st.caption(f"Showing {start_idx + 1}-{min(end_idx, len(df))} of {len(df)} records")


def display_schema_info(schema_info: Dict[str, Any]):
    """Display schema information and field descriptions."""
    with st.expander("Schema Information", expanded=False):
        st.write(f"**Dataset Type:** {schema_info['type']}")
        st.write(f"**Description:** {schema_info['description']}")
        
        st.subheader("Fields")
        
        field_data = []
        for field_name, field_info in schema_info["fields"].items():
            field_data.append({
                "Field": field_name,
                "Type": field_info["type"],
                "Description": field_info["description"] or "No description",
                "Format": field_info.get("format") or "N/A",
                "Enum Values": ", ".join(field_info["enum"]) if field_info.get("enum") else "N/A"
            })
        
        if field_data:
            st.dataframe(pd.DataFrame(field_data), use_container_width=True, hide_index=True)


def main():
    st.set_page_config(page_title="Dataset Explorer", layout="wide")
    st.title("Dataset Explorer")
    
    st.markdown(
        """
        Explore datasets using their committed schemas to provide structured data views.
        Select a dataset from the dropdown to browse its data with schema-driven filtering and formatting.
        """
    )
    
    # Discover available datasets
    datasets = discover_datasets()
    
    if not datasets:
        st.error("No datasets found. Please ensure schema files are available in the schemas directory.")
        return
    
    # Dataset selection
    dataset_options = {info["name"]: dataset_type for dataset_type, info in datasets.items()}
    selected_name = st.selectbox("Select Dataset", options=list(dataset_options.keys()))
    
    if not selected_name:
        return
    
    selected_dataset = dataset_options[selected_name]
    dataset_info = datasets[selected_dataset]
    
    # Extract schema information
    schema_info = extract_schema_info(dataset_info["schema"])
    
    # Display dataset metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Dataset", selected_name)
    with col2:
        st.metric("Schema File", Path(dataset_info["schema_file"]).name)
    with col3:
        st.metric("Fields", len(schema_info["fields"]))
    
    # Display schema information
    display_schema_info(schema_info)
    
    # Load dataset data
    with st.spinner("Loading dataset..."):
        df = load_dataset_data(selected_dataset)
    
    if df is None:
        st.error(f"Unable to load data for dataset '{selected_dataset}' from the public URL.")
        st.info("Please check your internet connection and try again. The dataset explorer requires access to the public Ukulele Tuesday datasets.")
        return
    
    # Show dataset overview
    st.header("Dataset Overview")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Records", len(df))
    with col2:
        st.metric("Columns", len(df.columns))
    
    # Create filters
    filters = create_data_filters(df, schema_info)
    
    # Apply filters
    filtered_df = apply_filters(df, filters)
    
    # Show filtered count
    if filters:
        st.info(f"Showing {len(filtered_df)} of {len(df)} records after applying filters.")
    
    # Sorting
    sort_column = st.selectbox("Sort by", options=["None"] + list(df.columns))
    if sort_column != "None":
        sort_order = st.radio("Sort order", ["Ascending", "Descending"], horizontal=True)
        ascending = sort_order == "Ascending"
        filtered_df = filtered_df.sort_values(by=sort_column, ascending=ascending)
    
    # Display data table
    st.header("Data")
    display_data_table(filtered_df, schema_info)
    
    # Summary statistics for numeric columns
    numeric_cols = filtered_df.select_dtypes(include=['number']).columns
    if not numeric_cols.empty:
        st.header("Summary Statistics")
        st.dataframe(filtered_df[numeric_cols].describe(), use_container_width=True)


if __name__ == "__main__":
    main()