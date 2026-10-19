"""初始化种子数据（还原 prototype.html 演示数据）。"""
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import CourseMaterial, Period, ScheduleItem, StudyPlan, Term, User
from app.services import rag_service

USERS = [
    {"username": "aaa", "password": "123456", "nickname": "小黑", "major": "计算机科学与技术", "grade": "大三"},
    {"username": "bbb", "password": "123456", "nickname": "小林", "major": "软件工程", "grade": "大二"},
]

TERMS = [{"label": "2026-2027学年 第一学期", "is_current": True}]

PERIODS = [
    (1, "第 1-2 节", "08:00 - 09:35", "周一 (今天)", 0),
    (2, "第 3-4 节", "10:00 - 11:35", "周二", 1),
    (3, "第 5-6 节", "14:00 - 15:35", "周三", 2),
    (4, "第 7-8 节", "16:00 - 17:35", "周四", 3),
    (5, "第 9-10 节", "19:00 - 20:35", "周五", 4),
]

SCHEDULES = {
    "aaa": [
        (1, 1, "08:00 - 09:35", "高等工程数学", "周明远 教授", "一教 A203", "1-16周", "blue", "高数"),
        (1, 2, "10:00 - 11:35", "操作系统原理", "陈振华 教授", "信息楼 B302", "1-16周", "emerald", "操作系统"),
        (1, 3, "14:00 - 15:35", "深度学习导论", "沈逸飞 副教授", "智算中心 104", "1-16周", "purple", "深度学习"),
        (2, 2, "10:00 - 11:35", "计算机网络", "周敏 副教授", "信息楼 A208", "1-16周", "amber", "计算机网络"),
        (3, 1, "08:00 - 09:35", "操作系统原理 (实验)", "陈振华 教授", "机房 C401", "2-16双周", "emerald", "操作系统"),
        (3, 3, "14:00 - 15:35", "数据库系统概论", "刘志远 教授", "信息楼 A405", "1-16周", "rose", "数据库"),
        (4, 2, "10:00 - 11:35", "深度学习导论", "沈逸飞 副教授", "智算中心 104", "1-16周", "purple", "深度学习"),
        (5, 2, "10:00 - 11:35", "大模型与智能体开发", "林牧 副教授", "智算中心 204", "1-12周", "indigo", "智能体"),
    ],
    "bbb": [
        (1, 2, "10:00 - 11:35", "软件工程导论", "吴建国 教授", "软院楼 102", "1-16周", "blue", "软件工程"),
        (1, 4, "16:00 - 17:35", "Web前端架构设计", "林晓 讲师", "软院楼 305", "1-16周", "emerald", "前端"),
        (3, 2, "10:00 - 11:35", "数据库系统概论", "刘志远 教授", "信息楼 A405", "1-16周", "rose", "数据库"),
    ],
}

MATERIALS = [
    ("操作系统原理", "COMP3011", "《Operating Systems: Three Easy Pieces》讲义 PDF、xv6 实验手册 v2.4",
     "进程调度算法（MLFQ）、虚拟内存页表转换、死锁四个必要条件与银行家算法、文件系统 Inode 结构。"),
    ("深度学习导论", "AINT3050", "PyTorch 算子实战讲义、反向传播推导笔记、Transformer 论文精读 PPT",
     "梯度消失与残差连接（ResNet）、BatchNorm 原理、Self-Attention 矩阵缩放点积计算、Adam 优化器公式。"),
    ("计算机网络", "COMP3042", "《计算机网络：自顶向下方法》第8版课件、Wireshark 抓包实验指导书",
     "TCP 三次握手与四次挥手状态机、拥塞控制（慢开始/拥塞避免/快重传）、OSPF 与 BGP 路由协议对比。"),
    ("数据库系统概论", "COMP3080", "SQL 优化实验文档、B+ 树索引源码剖析、事务 ACID 与 MVCC 讲义",
     "BCNF 范式分解、B+ 树聚簇索引与非聚簇索引、两阶段锁协议 (2PL)、Redo/Undo 日志恢复机制。"),
    ("大模型与智能体开发", "AINT3120", "Spring AI / LangChain4j 实战手册、ReAct 论文与 Tool Calling 接口规范",
     "Prompt 工程、RAG 向量切片与混合检索、Function Calling 工具注册、记忆管理 (ChatMemory)。"),
]

PLANS = [
    ("aaa", "《操作系统原理》第5周课前预习计划", "预习计划", "进行中",
     ["通读教材第 18-20 章：分页机制与多级页表设计（约 45 分钟）",
      "理解 TLB（快表）未命中时的硬件与操作系统处理流程",
      "运行 xv6 Lab2 分页实验环境，阅读 vm.c 核心函数源码"]),
    ("aaa", "《计算机网络》期中复习冲刺计划", "复习计划", "进行中",
     ["整理传输层 UDP 与 TCP 报文首部字段对比思维导图",
      "重做第 3 章课后计算题：序号、确认号与滑动窗口大小计算",
      "复盘 Wireshark 实验二：分析 HTTP 与 TCP 拥塞窗口变化曲线"]),
    ("aaa", "《大模型与智能体开发》校园课程助手项目实践计划", "预习计划", "已完成",
     ["熟悉课表查询 Tool、课程资料检索 Tool 与学习计划保存 Tool 的参数定义",
      "测试多轮对话上下文记忆：先生成草稿计划，用户确认说「保存」再触发入库"]),
]


def seed() -> None:
    db = SessionLocal()
    try:
        from app.models import entities  # noqa: F401
        from app.core.database import Base, engine

        Base.metadata.create_all(bind=engine)

        if db.scalars(select(Term)).first() is None:
            for t in TERMS:
                db.add(Term(label=t["label"], is_current=t["is_current"]))
            db.commit()
            print("seed: terms created")
        else:
            print("seed: terms exist, skip")

        if db.scalars(select(Period)).first() is None:
            for order, (slot, name, tr, label, wd) in enumerate(PERIODS):
                db.add(
                    Period(slot=slot, name=name, time_range=tr, day_label=label,
                           weekday=wd, sort_order=order)
                )
            db.commit()
            print("seed: periods created")
        else:
            print("seed: periods exist, skip")

        if db.scalars(select(User)).first() is None:
            for u in USERS:
                db.add(
                    User(
                        username=u["username"],
                        hashed_password=hash_password(u["password"]),
                        nickname=u["nickname"],
                        major=u["major"],
                        grade=u["grade"],
                    )
                )
            db.commit()
            print("seed: users created")
        else:
            print("seed: users exist, skip")

        if db.scalars(select(ScheduleItem)).first() is None:
            for username, rows in SCHEDULES.items():
                user = db.scalar(select(User).where(User.username == username))
                for day, slot, tr, name, teacher, room, weeks, color, mk in rows:
                    db.add(
                        ScheduleItem(
                            user_id=user.id, day=day, slot=slot, time_range=tr,
                            course_name=name, teacher=teacher, room=room,
                            weeks=weeks, color=color, material_key=mk,
                        )
                    )
            db.commit()
            print("seed: schedule created")
        else:
            print("seed: schedule exist, skip")

        if db.scalars(select(CourseMaterial)).first() is None:
            for course, code, docs, focus in MATERIALS:
                db.add(CourseMaterial(course=course, code=code, docs=docs, focus=focus))
            db.commit()
            print("seed: materials created")
        else:
            print("seed: materials exist, skip")

        if db.scalars(select(StudyPlan)).first() is None:
            for username, title, ptype, status, items in PLANS:
                user = db.scalar(select(User).where(User.username == username))
                db.add(
                    StudyPlan(
                        user_id=user.id, title=title, plan_type=ptype, status=status, items=items
                    )
                )
            db.commit()
            print("seed: plans created")
        else:
            print("seed: plans exist, skip")

        n = rag_service.sync_index(db)
        print(f"seed: chroma synced {n} docs")
    finally:
        db.close()
