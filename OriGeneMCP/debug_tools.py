# debug_tools.py
import sys
import os

# 确保能导入 src 模块
sys.path.append(os.getcwd())

from tools.ncbi.pubmed_search import PubMedSearch

def test_pubmed():
    print("\n🧪 Testing PubMed API Connectivity...")
    try:
        tool = PubMedSearch()
        # 使用一个肯定有结果的简单查询
        query = "Pembrolizumab"
        result = tool.search(query)
        
        if "Error" in result:
            print(f"❌ PubMed API Failed: {result}")
        elif "No PubMed articles" in result:
            print("⚠️ PubMed Connected but returned no results (Check date filter).")
        else:
            print("✅ PubMed API Success!")
            print(f"   Sample Output length: {len(result)} chars")
            print(f"   Snippet: {result[:200]}...")
            
    except Exception as e:
        print(f"❌ Exception during PubMed test: {e}")
        print("💡 Hint: Check your internet connection or Proxy settings.")

if __name__ == "__main__":
    print("=== OriGene Tool Debugger ===")
    test_pubmed()