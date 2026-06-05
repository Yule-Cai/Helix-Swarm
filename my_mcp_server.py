# my_mcp_server.py
from mcp.server.fastmcp import FastMCP
import datetime

# 初始化一个名为 "Helix-Tools" 的 MCP 服务器
mcp = FastMCP("Helix-Tools")

@mcp.tool()
def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """获取指定时区的当前精确时间。当用户询问时间或日期时使用。"""
    return f"Current time in {timezone} is {datetime.datetime.now()}"

@mcp.tool()
def query_weather(city: str) -> str:
    """查询指定城市的天气预报。"""
    # 这里我们用模拟数据，真实情况你可以接第三方 API
    mock_weather = {
        "北京": "晴朗，气温 22°C，微风",
        "上海": "多云，气温 25°C，适合出行",
        "深圳": "雷阵雨，气温 28°C，请带好雨伞"
    }
    return mock_weather.get(city, f"找不到 {city} 的天气数据，大概率是晴天！")

if __name__ == "__main__":
    # 启动 stdio 通信模式，准备被 Helix-Swarm 大脑接管！
    mcp.run()