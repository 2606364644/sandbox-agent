"""
沙箱Agent主入口
从Excel文件读取漏洞数据并执行PoC生成工作流
"""

import asyncio
import os
import sys
import pandas as pd
import argparse
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
from tqdm import tqdm
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.workflow import Workflow
from src.utils.logger import log


def read_vulnerabilities(excel_path: str, code_repo: str) -> List[Dict[str, Any]]:
    """读取Excel中的漏洞数据"""
    try:
        log.info(f"输入: 开始读取Excel文件 {excel_path}")

        # 读取Excel文件
        df = pd.read_excel(excel_path)
        log.info(f"成功读取Excel文件，共 {len(df)} 行数据")
        log.info(f"Excel文件列名: {list(df.columns)}")

        # 转换为漏洞数据字典列表
        vulnerabilities = []
        for index, row in df.iterrows():
            vuln_data = {
                'id': f"vuln_{index+1:03d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'vulnerability_type': row.get('type', 'UNKNOWN'),
                'description': row.get('description', ''),
                'filename': row.get('filename', ''),
                'code': row.get('code', ''),
                'impact': row.get('impact', ''),
                'initial_analysis': row.get('result', ''),
                'code_repo': code_repo
            }
            vulnerabilities.append(vuln_data)

        log.info(f"输出: 成功解析 {len(vulnerabilities)} 个漏洞数据")
        return vulnerabilities

    except Exception as e:
        log.error(f"错误: 读取Excel文件失败 - {e}")
        raise


async def process_vulnerability(workflow: Workflow, vuln: Dict[str, Any]) -> Dict[str, Any]:
    """处理单个漏洞"""
    start_time = time.time()
    log.info(f"开始处理漏洞: {vuln['id']} - {vuln['vulnerability_type']} - {vuln['filename']}")

    try:
        # 运行工作流
        result = await workflow.run(
            code_repo=vuln['code_repo'],
            vulnerability_type=vuln['vulnerability_type'],
            description=vuln['description'],
            filename=vuln['filename'],
            code=vuln['code'],
            impact=vuln['impact'],
            initial_analysis=vuln['initial_analysis']
        )

        # 计算处理时间
        processing_time = time.time() - start_time

        # 保存结果摘要
        summary = {
            'vulnerability_id': vuln['id'],
            'vulnerability_type': vuln['vulnerability_type'],
            'filename': vuln['filename'],
            'success': result.get('success', False),
            'iterations': result.get('retry_count', 0),
            'final_evaluation': str(result.get('sandbox_result', {})),
            'poc_path': result.get('poc_path', ''),
            'processing_time': processing_time,
            'timestamp': datetime.now().isoformat()
        }

        status = '成功' if summary['success'] else '失败'
        log.info(f"漏洞 {vuln['id']} 处理完成 - 状态: {status} - 耗时: {processing_time:.2f}秒")
        return summary

    except Exception as e:
        processing_time = time.time() - start_time
        log.error(f"处理漏洞 {vuln['id']} 时发生错误: {e} - 耗时: {processing_time:.2f}秒")
        return {
            'vulnerability_id': vuln['id'],
            'vulnerability_type': vuln['vulnerability_type'],
            'filename': vuln['filename'],
            'success': False,
            'error': str(e),
            'processing_time': processing_time,
            'timestamp': datetime.now().isoformat()
        }


async def process_vulnerabilities(workflow: Workflow, vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量处理漏洞 - 支持并发和进度条"""
    total_count = len(vulnerabilities)
    log.info(f"输入: 开始批量处理 {total_count} 个漏洞")

    results = []
    start_time = time.time()

    # 使用tqdm创建进度条
    with tqdm(total=total_count, desc="处理漏洞", unit="个",
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar:

        # 创建任务列表
        tasks = [process_vulnerability(workflow, vuln) for vuln in vulnerabilities]

        # 使用as_completed按完成顺序处理结果
        for completed_task in asyncio.as_completed(tasks):
            result = await completed_task
            results.append(result)

            # 更新进度条
            current_count = len(results)
            successful_count = sum(1 for r in results if r.get('success', False))

            # 更新进度条描述和后缀
            vuln_id = result.get('vulnerability_id', 'unknown')[:15]
            pbar.set_description(f"处理漏洞 {vuln_id}...")
            pbar.update(1)
            pbar.set_postfix({
                '成功': f"{successful_count}/{current_count}",
                '成功率': f"{successful_count/current_count*100:.1f}%",
                '平均耗时': f"{sum(r.get('processing_time', 0) for r in results)/current_count:.1f}s"
            })

    # 统计总时间
    total_time = time.time() - start_time
    successful_count = sum(1 for r in results if r.get('success', False))
    failed_count = total_count - successful_count

    log.info(f"输出: 批量处理完成 - 成功: {successful_count}/{total_count}")
    log.info(f"总耗时: {total_time:.2f}秒 - 平均每个漏洞: {total_time/total_count:.2f}秒")
    log.info(f"成功率: {successful_count/total_count*100:.1f}% - 成功: {successful_count}, 失败: {failed_count}")

    return results


def export_results(results: List[Dict[str, Any]], output_dir: str = "./results") -> tuple:
    """导出结果到文件"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 导出详细结果到Excel
    excel_filename = f"poc_workflow_results_{timestamp}.xlsx"
    excel_path = output_path / excel_filename

    try:
        df = pd.DataFrame(results)
        df.to_excel(excel_path, index=False, engine='openpyxl')
        log.info(f"输出: 详细结果已导出到 {excel_path}")
    except Exception as e:
        log.error(f"错误: 导出Excel失败 - {e}")
        raise

    # 导出摘要报告
    summary_filename = f"poc_workflow_summary_{timestamp}.txt"
    summary_path = output_path / summary_filename

    try:
        successful_count = sum(1 for r in results if r.get('success', False))
        failed_count = len(results) - successful_count

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("PoC工作流执行摘要报告\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总处理数量: {len(results)}\n\n")

            f.write("执行统计:\n")
            f.write(f"  成功: {successful_count}\n")
            f.write(f"  失败: {failed_count}\n")
            f.write(f"  成功率: {successful_count/len(results)*100:.1f}%\n\n")

            # 时间统计
            processing_times = [r.get('processing_time', 0) for r in results]
            total_processing_time = sum(processing_times)
            avg_processing_time = total_processing_time / len(results) if results else 0
            min_time = min(processing_times) if processing_times else 0
            max_time = max(processing_times) if processing_times else 0

            f.write("时间统计:\n")
            f.write(f"  总处理时间: {total_processing_time:.2f} 秒\n")
            f.write(f"  平均处理时间: {avg_processing_time:.2f} 秒\n")
            f.write(f"  最快处理时间: {min_time:.2f} 秒\n")
            f.write(f"  最慢处理时间: {max_time:.2f} 秒\n\n")

            f.write("详细结果:\n")
            f.write("-" * 50 + "\n")

            for result in results:
                f.write(f"漏洞ID: {result.get('vulnerability_id', 'N/A')}\n")
                f.write(f"类型: {result.get('vulnerability_type', 'N/A')}\n")
                f.write(f"文件: {result.get('filename', 'N/A')}\n")
                f.write(f"状态: {'成功' if result.get('success', False) else '失败'}\n")
                f.write(f"处理时间: {result.get('processing_time', 0):.2f} 秒\n")

                if result.get('success', False):
                    f.write(f"重试次数: {result.get('iterations', 0)}\n")
                    f.write(f"PoC路径: {result.get('poc_path', 'N/A')}\n")
                else:
                    f.write(f"错误信息: {result.get('error', 'N/A')}\n")

                f.write("\n")

        log.info(f"输出: 摘要报告已导出到 {summary_path}")
        return str(excel_path), str(summary_path)

    except Exception as e:
        log.error(f"错误: 导出摘要报告失败 - {e}")
        raise


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="沙箱Agent - 从Excel文件读取漏洞数据并执行PoC生成工作流",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                                    # 使用默认参数
  python main.py -e data.xlsx                      # 指定Excel文件
  python main.py -c /path/to/repo                  # 指定代码仓库
  python main.py -e data.xlsx -c /path/to/repo     # 指定Excel文件和代码仓库
  python main.py -e data.xlsx -i 5                 # 指定Excel文件和最大迭代次数
        """
    )

    parser.add_argument(
        '-e', '--excel',
        type=str,
        default='./format-af-result.xlsx',
        help='Excel文件路径 (默认: ./format-af-result.xlsx)'
    )

    parser.add_argument(
        '-c', '--code-repo',
        type=str,
        default='/codesec/AF8048/AF8.0.48',
        help='代码仓库路径 (默认: /codesec/AF8048/AF8.0.48)'
    )

    parser.add_argument(
        '-i', '--iterations',
        type=int,
        default=3,
        help='最大迭代次数 (默认: 3)'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        default='./outputs',
        help='结果输出目录 (默认: ./outputs)'
    )

    return parser.parse_args()


async def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()

    log.info("启动沙箱Agent主程序")
    log.info(f"配置参数 - Excel文件: {args.excel}, 代码仓库: {args.code_repo}, 最大迭代次数: {args.iterations}, 输出目录: {args.output}")

    try:
        # 第一步：读取Excel数据
        log.info("步骤1: 读取漏洞数据")
        vulnerabilities = read_vulnerabilities(args.excel, args.code_repo)

        if not vulnerabilities:
            log.error("Excel文件中没有找到有效的漏洞数据")
            return

        # 第二步：处理漏洞数据
        log.info("步骤2: 执行PoC生成工作流")
        workflow = Workflow(max_retries=args.iterations)
        results = await process_vulnerabilities(workflow, vulnerabilities)

        # 第三步：导出结果
        log.info("步骤3: 导出执行结果")
        excel_result_path, summary_path = export_results(results, args.output)

        # 输出最终统计
        successful_count = sum(1 for r in results if r.get('success', False))
        total_count = len(results)

        log.info("执行完成统计:")
        log.info(f"  总处理数量: {total_count}")
        log.info(f"  成功数量: {successful_count}")
        log.info(f"  失败数量: {total_count - successful_count}")
        log.info(f"  成功率: {successful_count/total_count*100:.1f}%")
        log.info(f"  详细结果文件: {excel_result_path}")
        log.info(f"  摘要报告文件: {summary_path}")

        log.info("程序执行完成")

    except Exception as e:
        log.error(f"程序执行失败: {e}")
        raise


if __name__ == "__main__":
    # 安装必要的依赖
    try:
        import openpyxl
    except ImportError:
        log.info("正在安装openpyxl依赖...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
        import openpyxl

    # 运行主程序
    asyncio.run(main())