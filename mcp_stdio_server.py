"""
MCP stdio 服务器（用于 Claude Desktop App）
通过 stdin/stdout 与 Claude Desktop 通信
符合 MCP (Model Context Protocol) 规范
"""
import sys
import io
import json
import asyncio
import logging

# 显式导入 cryptography 以确保 pymysql 可以正确使用它（必须在导入数据库模块之前）
try:
    import cryptography  # noqa: F401
except ImportError:
    import sys
    sys.stderr.write("警告: cryptography 未安装，数据库连接可能失败\n")
    sys.stderr.flush()

from mcp_server import mcp_server

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# 配置日志输出到 stderr（避免干扰 JSON-RPC 通信）
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

def get_tools_list():
    """获取可用工具列表（MCP 协议要求）"""
    tools = []
    
    # 定义每个工具的详细 schema
    tool_schemas = {
        'get_stock_list': {
            'description': '获取股票列表，支持关键词搜索',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'keyword': {
                        'type': 'string',
                        'description': '搜索关键词（股票名称或代码），可选'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': '返回数量限制，默认50',
                        'default': 50
                    }
                }
            }
        },
        'get_stock_secid': {
            'description': '便捷查询股票代码和交易所信息。输入股票名称（如"中国平安"），返回股票代码、交易所代码（SZ/SH）和secid',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'stock_name': {
                        'type': 'string',
                        'description': '股票名称，必填（如"中国平安"、"平安银行"）'
                    }
                },
                'required': ['stock_name']
            }
        },
        'get_stock_health': {
            'description': '获取股票健康度评分',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'secid': {
                        'type': 'string',
                        'description': '股票完整代码，必填（如 "1.600118"）'
                    },
                    'date': {
                        'type': 'string',
                        'description': '评分日期，格式 YYYY-MM-DD，可选'
                    }
                },
                'required': ['secid']
            }
        },
        'get_stock_history': {
            'description': '获取股票历史资金流向数据',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'secid': {
                        'type': 'string',
                        'description': '股票完整代码，必填（如 "1.600118"）'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': '返回记录数，默认30',
                        'default': 30
                    },
                    'days': {
                        'type': 'integer',
                        'description': '最近N天的数据，可选'
                    }
                },
                'required': ['secid']
            }
        },
        'get_realtime_capital_flow': {
            'description': '获取实时资金流向TOP股票',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'limit': {
                        'type': 'integer',
                        'description': '返回数量，默认20',
                        'default': 20
                    }
                }
            }
        },
        'get_index_data': {
            'description': '获取主要指数数据（上证指数、深证成指等）',
            'inputSchema': {
                'type': 'object',
                'properties': {}
            }
        },
        'analyze_stock_trend': {
            'description': '分析股票趋势',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'secid': {
                        'type': 'string',
                        'description': '股票完整代码，必填（如 "1.600118"）'
                    },
                    'days': {
                        'type': 'integer',
                        'description': '分析天数，默认30',
                        'default': 30
                    }
                },
                'required': ['secid']
            }
        },
        'compare_stocks': {
            'description': '比较多只股票的健康度',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'secids': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': '股票完整代码数组，必填（如 ["1.600118", "0.000001"]）'
                    }
                },
                'required': ['secids']
            }
        },
        'sync_stock_list': {
            'description': '同步股票列表到数据库（注意：此操作可能需要较长时间）',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'delay': {
                        'type': 'number',
                        'description': '每次请求延迟时间（秒），默认1.0',
                        'default': 1.0
                    }
                }
            }
        },
        'sync_stock_history': {
            'description': '同步股票历史资金数据到数据库（注意：此操作可能需要较长时间）',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'secid': {
                        'type': 'string',
                        'description': '股票完整代码，可选（不提供则同步所有股票）'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': '每只股票获取的历史数据条数，默认250',
                        'default': 250
                    },
                    'delay': {
                        'type': 'number',
                        'description': '每只股票请求后的延迟时间（秒），默认1.0',
                        'default': 1.0
                    }
                }
            }
        }
    }
    
    for tool_name in mcp_server.tools.keys():
        schema = tool_schemas.get(tool_name, {
            'description': f'执行 {tool_name} 操作',
            'inputSchema': {
                'type': 'object',
                'properties': {}
            }
        })
        
        tools.append({
            'name': tool_name,
            'description': schema['description'],
            'inputSchema': schema['inputSchema']
        })
    
    return tools

async def handle_mcp_request(request):
    """处理 MCP 协议请求"""
    method = request.get('method')
    params = request.get('params', {})
    request_id = request.get('id')
    
    # 检查是否为通知（没有 id 的请求）
    is_notification = request_id is None
    
    # 确保 id 不为 None（MCP 协议要求，但通知除外）
    if request_id is None and not is_notification:
        request_id = 0
    
    # 处理通知（notifications/*）
    if method and method.startswith('notifications/'):
        # 通知不需要响应，返回 None 表示不发送响应
        if method == 'notifications/initialized':
            # 初始化通知，不响应
            return None
        # 其他通知也忽略
        return None
    
    # 处理 MCP 标准方法
    if method == 'initialize':
        # 初始化请求
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'protocolVersion': '2024-11-05',
                'capabilities': {
                    'tools': {}
                },
                'serverInfo': {
                    'name': 'flowinsight',
                    'version': '1.0.0'
                }
            }
        }
    
    elif method == 'tools/list':
        # 返回工具列表
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'tools': get_tools_list()
            }
        }
    
    elif method == 'tools/call':
        # 调用工具
        tool_name = params.get('name')
        tool_args = params.get('arguments', {})
        
        if tool_name not in mcp_server.tools:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32601,
                    'message': f'Tool not found: {tool_name}'
                }
            }
        
        try:
            # 调用工具
            result = await mcp_server.tools[tool_name](tool_args)
            
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'content': [
                        {
                            'type': 'text',
                            'text': json.dumps(result, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32603,
                    'message': str(e)
                }
            }
    
    elif method == 'ping':
        # Ping 请求
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {}
        }
    
    else:
        # 未知方法，尝试作为自定义方法处理
        try:
            result = await mcp_server.handle_request(method, params)
            result['id'] = request_id
            return result
        except Exception:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32601,
                    'message': f'Method not found: {method}'
                }
            }

async def main():
    """主循环：从 stdin 读取 JSON-RPC 请求，处理并返回响应到 stdout"""
    try:
        # 读取 stdin 的每一行
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                # 解析 JSON-RPC 请求
                request = json.loads(line)
                
                # 处理请求
                response = await handle_mcp_request(request)
                
                # 如果是通知（返回 None），不发送响应
                if response is not None:
                    # 输出响应到 stdout
                    response_json = json.dumps(response, ensure_ascii=False)
                    print(response_json, flush=True)
                
            except json.JSONDecodeError as parse_error:
                # JSON 解析错误
                error_response = {
                    'jsonrpc': '2.0',
                    'error': {
                        'code': -32700,
                        'message': f'Parse error: {str(parse_error)}'
                    },
                    'id': 0  # 使用默认 id，不能为 null
                }
                print(json.dumps(error_response, ensure_ascii=False), flush=True)
                
            except Exception as exc:
                # 其他错误
                request_id = 0
                if 'request' in locals():
                    request_id = request.get('id', 0)
                
                error_response = {
                    'jsonrpc': '2.0',
                    'error': {
                        'code': -32603,
                        'message': str(exc)
                    },
                    'id': request_id if request_id is not None else 0
                }
                print(json.dumps(error_response, ensure_ascii=False), flush=True)
                
    except KeyboardInterrupt:
        # 正常退出
        pass
    except Exception as e:
        # 致命错误
        error_response = {
            'jsonrpc': '2.0',
            'error': {
                'code': -32603,
                'message': f'Internal error: {str(e)}'
            },
            'id': 0  # 使用默认 id，不能为 null
        }
        print(json.dumps(error_response, ensure_ascii=False), flush=True)
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        sys.stderr.write(f"Fatal error: {e}\n")
        sys.exit(1)

