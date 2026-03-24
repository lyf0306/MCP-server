from graphql import build_schema
from graphql.language import parse
from graphql.validation import validate
from .base_tool import BaseTool
import requests
import copy
import logging  # 引入 logging 以便调试

def validate_query(query_str, schema_str):
    try:
        # Build the GraphQL schema object from the provided schema string
        schema = build_schema(schema_str)

        # Parse the query string into an AST (Abstract Syntax Tree)
        query_ast = parse(query_str)

        # Validate the query AST against the schema
        validation_errors = validate(schema, query_ast)

        if not validation_errors:
            return True
        else:
            # Collect and return the validation errors
            error_messages = '\n'.join(str(error)
                                       for error in validation_errors)
            return f"Query validation errors:\n{error_messages}"
    except Exception as e:
        return f"An error occurred during validation: {str(e)}"

def remove_none_and_empty_values(json_obj):
    """Remove all key-value pairs where the value is None or an empty list"""
    if isinstance(json_obj, dict):
        return {k: remove_none_and_empty_values(v) for k, v in json_obj.items() if v is not None and v != []}
    elif isinstance(json_obj, list):
        return [remove_none_and_empty_values(item) for item in json_obj if item is not None and item != []]
    else:
        return json_obj

def execute_query(endpoint_url, query, variables=None):
    try:
        # 发送请求
        response = requests.post(
            endpoint_url, json={'query': query, 'variables': variables})
        
        # 尝试解析 JSON
        try:
            result = response.json()
        except requests.exceptions.JSONDecodeError:
            print(f"JSONDecodeError: Could not decode response from {endpoint_url}")
            return None

        # 清理空值 (复用文件中的 remove_none_and_empty_values 函数)
        result = remove_none_and_empty_values(result)

        # [关键修复] 处理返回值为列表的情况
        # 某些 API 可能直接返回数据列表，此时调用 .get() 会导致崩溃
        if isinstance(result, list):
            return result

        # 确保 result 是字典后再进行标准 GraphQL 错误检查
        if isinstance(result, dict):
            # 检查是否包含 errors 字段
            if 'errors' in result:
                print("Invalid Query: ", result['errors'])
                return None
            
            # 检查 data 字段是否为空
            # 注意：这里增加了 isinstance(result, dict) 判断以防万一
            elif not result.get('data') or all(not v for v in result['data'].values()):
                print("No data returned")
                return None
            else:
                return result
        
        # 如果既不是 list 也不是 dict (极少见情况)，直接返回
        return result

    except Exception as e:
        print(f"Error executing query: {e}")
        return None

class GraphQLTool(BaseTool):
    def __init__(self, tool_config, endpoint_url):
        super().__init__(tool_config)
        self.endpoint_url = endpoint_url
        self.query_schema = tool_config['query_schema']
        self.parameters = tool_config['parameter']['properties']
        self.default_size = 5

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        if 'size' in self.parameters and 'size' not in arguments:
            arguments['size'] = 5
        
        # [新增] 移除 arguments 中值为 None 的项，防止 GraphQL 报错
        arguments = {k: v for k, v in arguments.items() if v is not None}
        
        return execute_query(endpoint_url=self.endpoint_url, query=self.query_schema, variables=arguments)


class OpentargetTool(GraphQLTool):
    def __init__(self, tool_config):
        endpoint_url = 'https://api.platform.opentargets.org/api/v4/graphql'
        super().__init__(tool_config, endpoint_url)
        
    def run(self, arguments):
        # [增强] 仅对字符串类型的 diseaseName 或 name 进行连字符替换
        # 防止误伤 ID 类型的参数
        for each_arg, arg_value in arguments.items():
            if isinstance(arg_value, str): 
                # 假设通常只有 name 类的字段需要替换 '-' 为 ' '
                if 'name' in each_arg.lower() or 'query' in each_arg.lower():
                    if '-' in arg_value:
                        arguments[each_arg] = arg_value.replace('-', ' ')
        return super().run(arguments)
            

class OpentargetToolDrugNameMatch(GraphQLTool):
    def __init__(self, tool_config, drug_generic_tool=None):
        endpoint_url = 'https://api.platform.opentargets.org/api/v4/graphql'
        self.drug_generic_tool = drug_generic_tool
        # [关键修复] 扩充可能的参数名列表，兼容 name 和 drug_name
        self.possible_drug_name_args = ['drugName', 'name', 'drug_name', 'queryString']
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        
        # 尝试直接执行
        results = execute_query(endpoint_url=self.endpoint_url, query=self.query_schema, variables=arguments)
        
        # 如果没有结果，尝试使用通用名搜索
        if results is None or (isinstance(results, dict) and not results.get('data')):
            print("No results found for the drug brand name. Trying with the generic name.")
            name_arguments = {}
            target_arg_key = None
            
            # 查找参数中是否存在药物名称相关的 key
            for each_args in self.possible_drug_name_args:
                if each_args in arguments:
                    name_arguments['drug_name'] = arguments[each_args]
                    target_arg_key = each_args
                    break
            
            if len(name_arguments) == 0:
                print("No drug name found in the arguments.")
                return None
            
            # 运行 FDA 工具查找通用名
            if self.drug_generic_tool:
                drug_name_results = self.drug_generic_tool.run(name_arguments)
                if drug_name_results is not None and 'openfda.generic_name' in drug_name_results:
                    generic_name = drug_name_results['openfda.generic_name']
                    # 更新参数，使用通用名重试
                    if target_arg_key:
                        arguments[target_arg_key] = generic_name
                        print("Found generic name. Trying with the generic name: ", generic_name)
                        results = execute_query(endpoint_url=self.endpoint_url, query=self.query_schema, variables=arguments)
        
        return results
            

class OpentargetGeneticsTool(GraphQLTool):
    def __init__(self, tool_config):
        endpoint_url = 'https://api.genetics.opentargets.org/graphql'
        super().__init__(tool_config, endpoint_url)