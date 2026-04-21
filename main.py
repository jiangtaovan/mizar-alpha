"""
K线技术指标向量化预测引擎 - 主程序入口
"""

from loguru import logger
from mizar.api.routes import create_app
from mizar.utils import load_config,setup_logging


__all__ = ['main']

def main():
    """主函数"""
    # 加载配置
    config = load_config()
    
    # 设置日志
    setup_logging(config)
    
    logger.info("=" * 60)
    logger.info("市场状态向量数据库服务启动")
    logger.info("=" * 60)
    
    # 导入 FastAPI 应用

    
    # 创建应用
    app = create_app(config)
    
    # 获取配置
    host = config.get('api', {}).get('host', '0.0.0.0')
    port = config.get('api', {}).get('port', 8000)
    
    logger.info(f"服务监听在 {host}:{port}")
    logger.info(f"API 文档地址：http://{host}:{port}/docs")
    
    # 启动服务
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
