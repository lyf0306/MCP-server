import requests
import logging
import time

logger = logging.getLogger(__name__)

class PubMedSearch:
    """
    Directly search PubMed using NCBI E-Utilities API.
    Strictly finds literature from 2024 to present.
    """
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def search(self, query: str, max_results: int = 5) -> str:
        """
        Args:
            query: Medical keywords (e.g. "Pembrolizumab endometrial cancer")
        """
        try:
            # 1. ESearch: Search for IDs
            # 限定日期：2024/01/01 至今
            term = f"{query} AND (2024/01/01:3000/12/31[pdat])" 
            search_params = {
                "db": "pubmed",
                "term": term,
                "retmode": "json",
                "retmax": max_results,
                "sort": "date"  # 按日期降序，获取最新的
            }
            
            # 建议在内网环境若无 API Key，请求频率需控制（每秒不超过3次）
            resp = requests.get(f"{self.BASE_URL}/esearch.fcgi", params=search_params, timeout=10)
            
            if resp.status_code != 200:
                return f"Error: PubMed API returned status {resp.status_code}"

            data = resp.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                return "No PubMed articles found from 2024-present for this query."

            # 2. ESummary: Get details
            ids = ",".join(id_list)
            summary_params = {
                "db": "pubmed",
                "id": ids,
                "retmode": "json"
            }
            summary_resp = requests.get(f"{self.BASE_URL}/esummary.fcgi", params=summary_params, timeout=10)
            summary_result = summary_resp.json().get("result", {})
            
            # 3. Format Output
            results = []
            for uid in id_list:
                # 'uids' 列表在 summary_result['uids'] 中，但直接用 uid key 访问详细项
                if uid not in summary_result: continue
                item = summary_result[uid]
                
                title = item.get("title", "No Title")
                pub_date = item.get("pubdate", "Unknown Date")
                source = item.get("source", "Unknown Journal")
                url = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
                
                results.append(f"Title: {title}\nDate: {pub_date}\nJournal: {source}\nURL: {url}\n")
            
            return "\n---\n".join(results)

        except Exception as e:
            logger.error(f"PubMed API Error: {e}")
            return f"Error searching PubMed: {str(e)}"