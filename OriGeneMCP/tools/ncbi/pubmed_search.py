import requests
import logging
import re
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class PubMedSearch:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def search(self, query: str, max_results: int = 5) -> str:
        try:
            term = query.replace("'", '"')
            search_params = {
                "db": "pubmed",
                "term": term,
                "retmode": "json",
                "retmax": max_results,
                "sort": "date"
            }
            # 增加超时时间到 15 秒
            resp = requests.post(f"{self.BASE_URL}/esearch.fcgi", data=search_params, timeout=15)
            
            if resp.status_code == 400:
                logger.warning(f"PubMed rejected complex query. Trying simplified fallback...")
                clean_term = re.sub(r'\[.*?\]', '', term)
                clean_term = clean_term.replace('"', '').replace("'", "")
                clean_term = re.sub(r'\b(AND|OR|NOT)\b', ' ', clean_term, flags=re.IGNORECASE)
                clean_term = re.sub(r'[\(\):]', ' ', clean_term)
                clean_term = re.sub(r'\s+', ' ', clean_term).strip()
                search_params["term"] = clean_term
                resp = requests.post(f"{self.BASE_URL}/esearch.fcgi", data=search_params, timeout=15)
                
            if resp.status_code != 200:
                return f"Error: PubMed API returned status {resp.status_code}"

            data = resp.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                return f"No PubMed articles found for query: {query}"

            ids = ",".join(id_list)
            fetch_params = {
                "db": "pubmed",
                "id": ids,
                "retmode": "xml"
            }
            # 🚀 致命修复：抓取全文摘要时增加超时到 30 秒！防止半路断开！
            fetch_resp = requests.post(f"{self.BASE_URL}/efetch.fcgi", data=fetch_params, timeout=30)
            
            try:
                root = ET.fromstring(fetch_resp.content)
            except ET.ParseError:
                return "Error parsing PubMed XML response."

            results = []
            for article in root.findall('.//PubmedArticle'):
                pmid = article.findtext('.//PMID', default="Unknown PMID")
                title = article.findtext('.//ArticleTitle', default="No Title")
                
                # 🚀 致命修复：使用 itertext() 提取摘要！这样无论里面有多少 <i> <b> 标签，都能把所有文字完美提取出来！
                abstract_texts = article.findall('.//AbstractText')
                if abstract_texts:
                    abstract = " ".join(["".join(a.itertext()).strip() for a in abstract_texts])
                else:
                    abstract = "No abstract available."
                    
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                results.append(f"PMID: {pmid}\nTitle: {title}\nAbstract: {abstract}\nURL: {url}")
            
            return "\n---\n".join(results)

        except Exception as e:
            logger.error(f"PubMed API Error: {e}")
            return f"Error searching PubMed: {str(e)}"
