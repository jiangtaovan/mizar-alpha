#!/usr/bin/env python3
"""
批量查询测试工具 - 评估系统性能

用法:
    python scripts/batch_query_test.py --queries 100 --top-k 10
"""

import argparse
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import time

API_URL = "http://localhost:8000"

def generate_random_features():
    """生成随机特征用于测试"""
    return {
        "MA_SMA_5": np.random.uniform(10, 20),
        "MA_SMA_20": np.random.uniform(10, 20),
        "MA_SMA_50": np.random.uniform(10, 20),
        "MA_SMA_200": np.random.uniform(9, 19),
        "MA_EMA_12": np.random.uniform(10, 20),
        "MA_EMA_26": np.random.uniform(10, 20),
        "ADX": np.random.uniform(15, 45),
        "SAR": np.random.uniform(10, 20),
        "RSI_RSI_6": np.random.uniform(30, 70),
        "RSI_RSI_12": np.random.uniform(35, 65),
        "RSI_RSI_24": np.random.uniform(40, 60),
        "MACD_macd": np.random.randn() * 0.5,
        "MACD_signal": np.random.randn() * 0.3,
        "MACD_histogram": np.random.randn() * 0.2,
        "CCI": np.random.uniform(-150, 150),
        "MOM": np.random.randn() * 2,
        "ROC": np.random.randn() * 5,
        "WILLR": np.random.uniform(-100, 0),
        "ATR_ATR": np.random.uniform(2, 4),
        "NATR": np.random.uniform(1, 3),
        "TRANGE": np.random.uniform(0.3, 0.6),
        "BBANDS_lower": np.random.uniform(9, 11),
        "BBANDS_middle": np.random.uniform(10, 12),
        "BBANDS_upper": np.random.uniform(11, 13),
        "VOLUME_RATIO": np.random.uniform(0.5, 3.0),
        "OBV": np.random.randint(1000000, 10000000),
        "CMF": np.random.uniform(-0.5, 0.5),
        "MFI": np.random.uniform(30, 70),
        "VWAP": np.random.uniform(10, 12),
        "patterns_CDL_DOJI": np.random.choice([0, 1]),
        "patterns_CDL_HAMMER": np.random.choice([0, 1]),
        "patterns_CDL_ENGULFING": np.random.choice([0, 1]),
        "patterns_CDL_MORNINGSTAR": np.random.choice([0, 1]),
        "patterns_CDL_EVENINGSTAR": np.random.choice([0, 1]),
        "patterns_CDL_DARKCLOUDCOVER": np.random.choice([0, 1]),
        "patterns_CDL_PIERCING": np.random.choice([0, 1]),
        "AROON_aroon_up": np.random.uniform(0, 100),
        "AROON_aroon_down": np.random.uniform(0, 100),
        "AROON_aroon_oscillator": np.random.uniform(-100, 100),
        "DMI_ADX": np.random.uniform(15, 45),
        "DMI_PLUS_DI": np.random.uniform(15, 40),
        "DMI_MINUS_DI": np.random.uniform(15, 40),
        "HISTORICAL_VOLATILITY_HV_20": np.random.uniform(0.2, 0.5),
        "HISTORICAL_VOLATILITY_HV_60": np.random.uniform(0.3, 0.6),
        "EFFICIENCY_RATIO": np.random.uniform(0.3, 0.8)
    }

def test_single_query(top_k=10):
    """单次查询测试"""
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{API_URL}/query",
            json={
                "features": generate_random_features(),
                "top_k": top_k,
                "weighting_method": "distance"
            },
            timeout=10
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'response_time': elapsed,
                'avg_ret_1d': result['prediction']['avg_ret_1d'],
                'up_probability': result['prediction']['up_probability'],
                'sample_size': result['prediction']['sample_size']
            }
        else:
            return {'success': False, 'error': response.text}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def batch_test(num_queries=100, top_k=10):
    """批量测试"""
    print(f"\n开始批量测试...")
    print(f"查询次数：{num_queries}")
    print(f"Top-K: {top_k}")
    print(f"API 地址：{API_URL}\n")
    
    results = []
    
    for i in range(num_queries):
        result = test_single_query(top_k)
        results.append(result)
        
        if (i + 1) % 20 == 0:
            print(f"已完成 {i+1}/{num_queries} 次查询")
    
    # 统计分析
    df = pd.DataFrame(results)
    successful = df[df['success'] == True]
    
    print("\n" + "=" * 60)
    print("📊 测试结果统计")
    print("=" * 60)
    
    if len(successful) == 0:
        print("\n❌ 所有查询都失败了！请检查 API 服务是否正常。")
        print(f"\n错误示例：{results[0].get('error', 'Unknown error')}")
        return
    
    print(f"\n✅ 成功率：{len(successful) / len(results) * 100:.1f}%")
    
    print(f"\n⏱️  响应时间统计:")
    print(f"   平均：{successful['response_time'].mean()*1000:.1f} ms")
    print(f"   中位数：{successful['response_time'].median()*1000:.1f} ms")
    print(f"   P95: {successful['response_time'].quantile(0.95)*1000:.1f} ms")
    print(f"   P99: {successful['response_time'].quantile(0.99)*1000:.1f} ms")
    print(f"   最快：{successful['response_time'].min()*1000:.1f} ms")
    print(f"   最慢：{successful['response_time'].max()*1000:.1f} ms")
    
    print(f"\n📈 预测效果统计:")
    print(f"   平均收益：{successful['avg_ret_1d'].mean():.2%}")
    print(f"   上涨概率：{successful['up_probability'].mean():.1%}")
    print(f"   平均样本数：{successful['sample_size'].mean():.1f}")
    
    # 性能评级
    print(f"\n🏆 性能评级:")
    avg_time = successful['response_time'].mean()
    if avg_time < 0.2:
        print(f"   响应速度：⭐⭐⭐⭐⭐ 优秀 (< 200ms)")
    elif avg_time < 0.5:
        print(f"   响应速度：⭐⭐⭐⭐ 良好 (< 500ms)")
    elif avg_time < 1.0:
        print(f"   响应速度：⭐⭐⭐ 合格 (< 1s)")
    else:
        print(f"   响应速度：⭐⭐ 需优化 (> 1s)")
    
    avg_prob = successful['up_probability'].mean()
    if avg_prob > 0.6:
        print(f"   预测信心：⭐⭐⭐⭐⭐ 优秀 (> 60%)")
    elif avg_prob > 0.55:
        print(f"   预测信心：⭐⭐⭐⭐ 良好 (> 55%)")
    elif avg_prob > 0.5:
        print(f"   预测信心：⭐⭐⭐ 及格 (> 50%)")
    else:
        print(f"   预测信心：⭐⭐ 需改进 (< 50%)")
    
    # 保存结果
    output_file = f"datas/batch_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False)
    print(f"\n💾 详细结果已保存至：{output_file}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='批量查询测试工具')
    parser.add_argument('--queries', '-q', type=int, default=100,
                       help='查询次数（默认 100）')
    parser.add_argument('--top-k', '-k', type=int, default=10,
                       help='返回相似状态数量（默认 10）')
    
    args = parser.parse_args()
    batch_test(args.queries, args.top_k)
