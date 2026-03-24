from typing import Optional, Union, Any
from asyncio import to_thread
from mcp.server.fastmcp import FastMCP

from tools.clinicaltrials.clinicaltrials_api import ClinicalTrialsAPI


mcp = FastMCP(
    name="clinicaltrials_mcp",
    stateless_http=True,
)
clinicaltrials_api = ClinicalTrialsAPI()


@mcp.tool()
async def get_studies(
   query: Optional[Union[dict, str]] = None,
    filter: Optional[Union[dict, str]] = None,
    post_filter: Optional[Union[dict, str]] = None,
    fields: Optional[list] = None,
    sort: Optional[list] = None,
    page_size: int = 50,
    page_token: Optional[str] = None,
    format: str = "json",
    markup_format: str = "markdown",
    count_total: bool = False
):
    """
    Search clinical trials with structured query parameters on ClinicalTrials.gov.
    Supports complex queries with query, filter and post-filter parameters.
    Returns paginated results with optional total count.
    
    Args:
        query: Parameters for query.* fields (e.g., {"cond": "cancer"})
        filter: Parameters for filter.* fields (e.g., {"status": "RECRUITING"})
        post_filter: Parameters for postFilter.* fields
        fields: List of fields to return (e.g., ["NCTId", "BriefTitle"])
        sort: Sort fields (e.g., ["@relevance", "EnrollmentCount:desc"])
        page_size: Number of results per page (max 1000)
        page_token: Token for next page
        format: Response format ("json" or "csv")
        markup_format: Text formatting ("markdown" or "legacy")
        count_total: Whether to include total count
        
    Returns:
        Dictionary containing:
        - studies: List of matching studies
        - next_page_token: Token for next page (if available)
        - total_count: Total number of studies (if count_total=True)
    
    Query example:  
        {'query': {'cond': 'cancer'}, 'filter': {'status': 'RECRUITING'}}
        {'query': {'cond': 'lung cancer'}, 'fields': ['NCTId', 'BriefTitle']}
        
    """
    if isinstance(query, str):
        query = {"cond": query}

    # [新增] 兼容性处理：如果 filter 是字符串，尝试解析或默认处理
    if isinstance(filter, str):
        if ":" in filter:
            try:
                # 尝试简单解析 "status:RECRUITING"
                parts = filter.split("|") # 处理可能的多个过滤器
                filter_dict = {}
                for part in parts:
                    if ":" in part:
                        k, v = part.split(":", 1)
                        filter_dict[k.strip()] = v.strip()
                if filter_dict:
                    filter = filter_dict
                else:
                    filter = {"overallStatus": filter}
            except:
                filter = {"overallStatus": filter}
        else:
            filter = {"overallStatus": filter}

    # 调用 API
    result = await to_thread(clinicaltrials_api.get_studies,
        query=query,
        filter=filter,
        post_filter=post_filter,
        fields=fields,
        sort=sort,
        page_size=page_size,
        page_token=page_token,
        format=format,
        markup_format=markup_format,
        count_total=count_total
    )

    # [关键修复] 防止 result 为 None 时崩溃
    if result is None:
        return {
            "studies": [],
            "next_page_token": None,
            "total_count": 0
        }

    return {
        "studies": result.get("studies", []),
        "next_page_token": result.get("nextPageToken"),
        "total_count": result.get("totalCount")
    }

@mcp.tool()
async def get_study(
    nct_id: str,
    format: str = "json",
    markup_format: str = "markdown",
    fields: Optional[list] = None
):
    """
    Get details for a single clinical trial.
    
    Args:
        nct_id: The NCT ID (e.g., "NCT000001")
        format: Response format ("json", "csv", etc.)
        markup_format: Text formatting ("markdown" or "legacy")
        fields: List of fields to include
        
    Returns:
        Dictionary containing study details
    
    Query example: {"nct_id": "NCT000001"}
    """
    return await to_thread(clinicaltrials_api.get_study,
        nct_id=nct_id,
        format=format,
        markup_format=markup_format,
        fields=fields
    )

@mcp.tool()
async def get_metadata(
    include_indexed_only: bool = False,
    include_historic_only: bool = False
):
    """
    Get metadata about available study fields.
    
    Args:
        include_indexed_only: Include indexed-only fields
        include_historic_only: Include historic-only fields
        
    Returns:
        Dictionary of field metadata
    """
    return await to_thread(clinicaltrials_api.get_metadata,
        include_indexed_only=include_indexed_only,
        include_historic_only=include_historic_only
    )

@mcp.tool()
async def get_search_areas():
    """
    Get available search documents and areas.
    
    Returns:
        Dictionary of search areas
    """
    return await to_thread(clinicaltrials_api.get_search_areas)

@mcp.tool()
async def get_enums():
    """
    Get enumeration types and values.
    
    Returns:
        Dictionary of enum types and values
    """
    return await to_thread(clinicaltrials_api.get_enums)

@mcp.tool()
async def get_study_size_stats():
    """
    Get statistics about study record sizes.
    
    Returns:
        Dictionary of size statistics
    """
    return await to_thread(clinicaltrials_api.get_study_size_stats)

@mcp.tool()
async def get_field_value_stats(fields: list[str], types: Optional[list[str]] = None):
    """
    Get value statistics for fields.
    
    Args:
        fields: List of field names
        types: Filter by data types (ENUM, STRING, etc.)
        
    Returns:
        Dictionary of field value statistics
    """
    return await to_thread(clinicaltrials_api.get_field_value_stats,
        fields=fields,
        types=types
    )

@mcp.tool()
async def get_field_size_stats(fields: Optional[list[str]] = None):
    """
    Get size statistics for list/array fields.
    
    Args:
        fields: List of field names to filter on
        
    Returns:
        Dictionary of field size statistics
    """
    return await to_thread(clinicaltrials_api.get_field_size_stats,
        fields=fields
    )

@mcp.prompt()
def system_prompt():
    return """You are the ClinicalTrials.gov MCP server. 
    You can answer questions about clinical trials using the ClinicalTrials.gov API.
    Always include the result of tool calls in your final answer."""

