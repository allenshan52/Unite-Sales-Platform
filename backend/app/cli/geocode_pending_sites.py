"""待编码单位地点任务入口：使用高德 Web 服务 Key 安全创建可展示的地图 pin。"""

from app.database import SessionLocal
from app.services.geocoding import geocode_pending_sites


def main() -> None:
    """执行最多一百条待编码地点，并输出不含凭据的结果摘要。"""

    with SessionLocal() as db:
        summary = geocode_pending_sites(db, limit=100, actor_username="system-geocode")
    print(f"地址编码完成：已定位 {summary.resolved} 条，低置信度 {summary.low_confidence} 条，待补地址 {summary.failed} 条，服务延期 {summary.deferred} 条。")


if __name__ == "__main__":
    main()
