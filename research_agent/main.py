"""
研究智能体主入口

提供命令行接口和交互式界面。
"""

import argparse
import asyncio
import sys
from typing import Optional
from loguru import logger

from research_agent.core import ResearchAgent
from research_agent.config import settings


def setup_logging() -> None:
    """配置日志"""
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    logger.add(
        settings.log_file,
        level=settings.log_level,
        rotation="10 MB",
        retention="7 days",
    )


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(
        description="研究智能体 - 学术研究助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  research-agent search "机器学习"
  research-agent analyze paper.pdf
  research-agent plan "深度学习研究"
  research-agent interactive
        """
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        choices=["search", "analyze", "plan", "interactive", "status"],
        default="interactive",
        help="执行的命令"
    )
    
    parser.add_argument(
        "args",
        nargs="*",
        help="命令参数"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )
    
    return parser.parse_args()


async def run_search(query: str, **kwargs) -> None:
    """
    执行搜索
    
    Args:
        query: 搜索查询
        **kwargs: 额外参数
    """
    agent = ResearchAgent()
    
    logger.info(f"搜索: {query}")
    
    result = await agent.search(query, **kwargs)
    
    print("\n" + "="*60)
    print("搜索结果")
    print("="*60)
    
    if result.get("success"):
        papers = result.get("papers", [])
        print(f"\n找到 {len(papers)} 篇论文:\n")
        
        for i, paper in enumerate(papers[:10], 1):
            print(f"{i}. {paper.get('title', '无标题')}")
            print(f"   作者: {', '.join(paper.get('authors', ['未知']))}")
            print(f"   年份: {paper.get('year', '未知')}")
            print(f"   引用: {paper.get('citation_count', 0)}")
            print()
    else:
        print(f"\n搜索失败: {result.get('error', '未知错误')}")


async def run_analyze(filepath: str, **kwargs) -> None:
    """
    执行分析
    
    Args:
        filepath: 文件路径
        **kwargs: 额外参数
    """
    agent = ResearchAgent()
    
    logger.info(f"分析: {filepath}")
    
    result = await agent.analyze(filepath, **kwargs)
    
    print("\n" + "="*60)
    print("分析结果")
    print("="*60)
    
    if result.get("success"):
        analysis = result.get("analysis", {})
        
        print(f"\n标题: {analysis.get('title', '未知')}")
        print(f"作者: {', '.join(analysis.get('authors', ['未知']))}")
        print(f"年份: {analysis.get('year', '未知')}")
        
        print("\n摘要:")
        print(analysis.get('abstract', '无摘要'))
        
        print("\n关键发现:")
        for i, finding in enumerate(analysis.get('key_findings', []), 1):
            print(f"  {i}. {finding}")
        
        print("\n方法论:")
        print(analysis.get('methodology', '未知'))
        
        print("\n局限性:")
        for i, limitation in enumerate(analysis.get('limitations', []), 1):
            print(f"  {i}. {limitation}")
    else:
        print(f"\n分析失败: {result.get('error', '未知错误')}")


async def run_plan(topic: str, **kwargs) -> None:
    """
    执行规划
    
    Args:
        topic: 研究主题
        **kwargs: 额外参数
    """
    agent = ResearchAgent()
    
    logger.info(f"规划: {topic}")
    
    result = await agent.plan(topic, **kwargs)
    
    print("\n" + "="*60)
    print("研究计划")
    print("="*60)
    
    if result.get("success"):
        plan = result.get("plan", {})
        
        print(f"\n主题: {plan.get('topic', '未知')}")
        print(f"时间范围: {plan.get('timeline', '未知')}")
        
        print("\n目标:")
        for i, goal in enumerate(plan.get('goals', []), 1):
            print(f"  {i}. {goal}")
        
        print("\n阶段:")
        for i, phase in enumerate(plan.get('phases', []), 1):
            print(f"\n  阶段 {i}: {phase.get('name', '未知')}")
            print(f"  时间: {phase.get('duration', '未知')}")
            print(f"  任务:")
            for j, task in enumerate(phase.get('tasks', []), 1):
                print(f"    {j}. {task}")
        
        print("\n资源:")
        for i, resource in enumerate(plan.get('resources', []), 1):
            print(f"  {i}. {resource}")
        
        print("\n风险:")
        for i, risk in enumerate(plan.get('risks', []), 1):
            print(f"  {i}. {risk}")
    else:
        print(f"\n规划失败: {result.get('error', '未知错误')}")


async def run_interactive() -> None:
    """运行交互式界面"""
    agent = ResearchAgent()
    
    print("\n" + "="*60)
    print("研究智能体 - 交互式界面")
    print("="*60)
    print("\n输入 'help' 查看帮助，输入 'quit' 退出\n")
    
    while True:
        try:
            # 获取用户输入
            user_input = input("\n研究智能体> ").strip()
            
            # 跳过空输入
            if not user_input:
                continue
            
            # 解析命令
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            # 处理命令
            if command in ["quit", "exit", "q"]:
                print("\n再见！")
                break
            
            elif command == "help":
                print("\n可用命令:")
                print("  search <查询>    - 搜索学术文献")
                print("  analyze <文件>   - 分析论文")
                print("  plan <主题>      - 制定研究计划")
                print("  status           - 查看状态")
                print("  help             - 显示帮助")
                print("  quit             - 退出")
            
            elif command == "search":
                if not args:
                    print("\n用法: search <查询>")
                    continue
                await run_search(args)
            
            elif command == "analyze":
                if not args:
                    print("\n用法: analyze <文件路径>")
                    continue
                await run_analyze(args)
            
            elif command == "plan":
                if not args:
                    print("\n用法: plan <研究主题>")
                    continue
                await run_plan(args)
            
            elif command == "status":
                status = agent.get_status()
                print("\n" + "="*60)
                print("系统状态")
                print("="*60)
                print(f"\n代理状态: {status.get('agent_status', '未知')}")
                print(f"运行时间: {status.get('uptime', '未知')}")
                print(f"总任务数: {status.get('total_tasks', 0)}")
                print(f"完成任务: {status.get('completed_tasks', 0)}")
                print(f"失败任务: {status.get('failed_tasks', 0)}")
            
            else:
                print(f"\n未知命令: {command}")
                print("输入 'help' 查看帮助")
        
        except KeyboardInterrupt:
            print("\n\n中断退出")
            break
        
        except Exception as e:
            logger.error(f"错误: {e}")
            print(f"\n错误: {e}")


async def run_status() -> None:
    """显示系统状态"""
    agent = ResearchAgent()
    
    status = agent.get_status()
    
    print("\n" + "="*60)
    print("研究智能体 - 系统状态")
    print("="*60)
    print(f"\n代理状态: {status.get('agent_status', '未知')}")
    print(f"运行时间: {status.get('uptime', '未知')}")
    print(f"总任务数: {status.get('total_tasks', 0)}")
    print(f"完成任务: {status.get('completed_tasks', 0)}")
    print(f"失败任务: {status.get('failed_tasks', 0)}")
    print(f"成功率: {status.get('success_rate', 0):.1%}")
    
    print("\n组件状态:")
    components = status.get('components', {})
    for name, state in components.items():
        print(f"  {name}: {state}")


def main() -> None:
    """主函数"""
    # 配置日志
    setup_logging()
    
    # 解析参数
    args = parse_args()
    
    # 执行命令
    try:
        if args.command == "search":
            if not args.args:
                print("错误: 搜索需要查询参数")
                sys.exit(1)
            asyncio.run(run_search(args.args[0]))
        
        elif args.command == "analyze":
            if not args.args:
                print("错误: 分析需要文件路径")
                sys.exit(1)
            asyncio.run(run_analyze(args.args[0]))
        
        elif args.command == "plan":
            if not args.args:
                print("错误: 规划需要研究主题")
                sys.exit(1)
            asyncio.run(run_plan(args.args[0]))
        
        elif args.command == "interactive":
            asyncio.run(run_interactive())
        
        elif args.command == "status":
            asyncio.run(run_status())
        
        else:
            asyncio.run(run_interactive())
    
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"程序错误: {e}")
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()