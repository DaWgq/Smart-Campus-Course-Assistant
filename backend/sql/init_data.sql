-- ============================================================
-- 校园课程智能助手 · 演示数据导入脚本
-- ------------------------------------------------------------
-- 特点：
--   1. 不删除任何表和数据，可重复执行（已存在的记录自动跳过）
--   2. 自动按用户名查找 user_id，无需手动改 ID
--   3. 库/表不存在时自动创建
--
-- 用法: Navicat 新建查询 -> 粘贴 -> 运行
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `campus_course_assistant`
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `campus_course_assistant`;

-- ------------------------------------------------------------
-- 建表（IF NOT EXISTS，已存在则跳过）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id`              INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
  `username`        VARCHAR(64)  NOT NULL COMMENT '登录用户名',
  `nickname`        VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '姓名/昵称',
  `major`           VARCHAR(128) NOT NULL DEFAULT '' COMMENT '专业',
  `grade`           VARCHAR(32)  NOT NULL DEFAULT '' COMMENT '年级',
  `role`            VARCHAR(16)  NOT NULL DEFAULT 'student' COMMENT '角色 student/admin，admin 可查看他人课表',
  `hashed_password` VARCHAR(255) NOT NULL COMMENT 'bcrypt密码哈希',
  `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生用户表';

CREATE TABLE IF NOT EXISTS `terms` (
  `id`         INT         NOT NULL AUTO_INCREMENT,
  `label`      VARCHAR(64) NOT NULL COMMENT '学期名称',
  `is_current` TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '是否当前学期',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_terms_label` (`label`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学年学期表';

CREATE TABLE IF NOT EXISTS `periods` (
  `id`         INT         NOT NULL AUTO_INCREMENT,
  `slot`       INT         NOT NULL COMMENT '第几节次',
  `name`       VARCHAR(64) NOT NULL COMMENT '节次名称',
  `time_range` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '上课时间段',
  `day_label`  VARCHAR(64) NOT NULL DEFAULT '' COMMENT '星期列标题',
  `weekday`    INT         NOT NULL DEFAULT 0 COMMENT '0=周一..4=周五',
  `sort_order` INT         NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_periods_slot` (`slot`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作息节次表';

CREATE TABLE IF NOT EXISTS `schedule_items` (
  `id`           INT          NOT NULL AUTO_INCREMENT,
  `user_id`      INT          NOT NULL COMMENT '所属用户',
  `day`          INT          NOT NULL COMMENT '1=周一..5=周五',
  `slot`         INT          NOT NULL COMMENT '第几节次',
  `time_range`   VARCHAR(64)  NOT NULL DEFAULT '',
  `course_name`  VARCHAR(128) NOT NULL COMMENT '课程名称',
  `teacher`      VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '任课教师',
  `room`         VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '上课地点',
  `weeks`        VARCHAR(64)  NOT NULL DEFAULT '1-16周' COMMENT '开课周次',
  `color`        VARCHAR(32)  NOT NULL DEFAULT 'blue' COMMENT '卡片配色',
  `material_key` VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '关联资料关键词',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_schedule_slot` (`user_id`,`day`,`slot`),
  KEY `ix_schedule_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生课表表';

CREATE TABLE IF NOT EXISTS `course_materials` (
  `id`     INT          NOT NULL AUTO_INCREMENT,
  `course` VARCHAR(128) NOT NULL COMMENT '课程名称',
  `code`   VARCHAR(32)  NOT NULL DEFAULT '' COMMENT '课程代码',
  `docs`   TEXT         NOT NULL COMMENT '教材与实验资料',
  `focus`  TEXT         NOT NULL COMMENT '核心考点',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_materials_course` (`course`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程资料表(RAG数据源)';

CREATE TABLE IF NOT EXISTS `study_plans` (
  `id`         INT          NOT NULL AUTO_INCREMENT,
  `user_id`    INT          NOT NULL COMMENT '所属用户',
  `title`      VARCHAR(255) NOT NULL COMMENT '计划标题',
  `plan_type`  VARCHAR(32)  NOT NULL DEFAULT '复习计划',
  `status`     VARCHAR(32)  NOT NULL DEFAULT '进行中',
  `items`      JSON         NOT NULL COMMENT '计划条目数组',
  `raw_draft`  TEXT         NOT NULL,
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_plans_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学习计划表';

CREATE TABLE IF NOT EXISTS `chat_sessions` (
  `id`         INT          NOT NULL AUTO_INCREMENT,
  `user_id`    INT          NOT NULL,
  `title`      VARCHAR(255) NOT NULL DEFAULT '新的对话',
  `history`    JSON         NOT NULL,
  `is_active`  TINYINT(1)   NOT NULL DEFAULT 1,
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_sessions_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话会话表';

-- ============================================================
--  1. 用户（密码统一 123456）
--     已存在同名用户则跳过，不会覆盖
--     注：以下 bcrypt 哈希仅对应公开演示账号（123456），
--         属课程设计用的测试数据，非真实凭据，可安全入库。
--         正式环境请通过注册接口创建用户，切勿复用这些哈希。
-- ============================================================
INSERT INTO `users` (`username`, `nickname`, `major`, `grade`, `role`, `hashed_password`)
SELECT * FROM (
  SELECT 'aaa',  '小黑', '计算机科学与技术', '大三', 'admin',    '$2b$12$HouRt9mvC4SFJJU1T9uBV.ln4V1ObT95jkKpXABut4bAB43BUH56e'
  UNION ALL SELECT 'bbb',  '小林', '软件工程',       '大二', 'student', '$2b$12$9fs9WhQN0x1KJ5NadeaOt.XrACwmJGTqu0Z92j2adhCqyPLnNmZ8O'
  UNION ALL SELECT 'ccc',  '小周', '人工智能',       '大二', 'student', '$2b$12$HouRt9mvC4SFJJU1T9uBV.ln4V1ObT95jkKpXABut4bAB43BUH56e'
  UNION ALL SELECT 'dawg', 'dawg', '计算机',         '大四', 'student', '$2b$12$HouRt9mvC4SFJJU1T9uBV.ln4V1ObT95jkKpXABut4bAB43BUH56e'
) AS t(username, nickname, major, grade, role, hashed_password)
WHERE NOT EXISTS (SELECT 1 FROM `users` u WHERE u.username = t.username);

-- ------------------------------------------------------------
--  角色与档案兜底：确保 role 非空、aaa 为管理员
-- ------------------------------------------------------------
UPDATE `users` SET `role` = 'student' WHERE `role` IS NULL OR `role` = '';
UPDATE `users` SET `role` = 'admin'    WHERE `username` = 'aaa';

-- ------------------------------------------------------------
--  为已有但信息不全的账号补全专业/年级（不改密码）
-- ------------------------------------------------------------
UPDATE `users` SET major = '计算机', grade = '大四' WHERE `username` = 'dawg' AND (major = '' OR major IS NULL);
UPDATE `users` SET nickname = 'dawg'  WHERE `username` = 'dawg' AND (nickname = '' OR nickname IS NULL);

-- ============================================================
--  2. 学年学期
-- ============================================================
INSERT INTO `terms` (`label`, `is_current`)
SELECT '2026-2027学年 第一学期', 1
WHERE NOT EXISTS (SELECT 1 FROM `terms` WHERE `label` = '2026-2027学年 第一学期');

UPDATE `terms` SET `is_current` = 0;
UPDATE `terms` SET `is_current` = 1 WHERE `label` = '2026-2027学年 第一学期';

-- ============================================================
--  3. 作息节次（课表格子）
-- ============================================================
INSERT INTO `periods` (`slot`, `name`, `time_range`, `day_label`, `weekday`, `sort_order`)
SELECT * FROM (
  SELECT 1, '第 1-2 节',  '08:00 - 09:35', '周一 (今天)', 0, 0
  UNION ALL SELECT 2, '第 3-4 节',  '10:00 - 11:35', '周二',        1, 1
  UNION ALL SELECT 3, '第 5-6 节',  '14:00 - 15:35', '周三',        2, 2
  UNION ALL SELECT 4, '第 7-8 节',  '16:00 - 17:35', '周四',        3, 3
  UNION ALL SELECT 5, '第 9-10 节', '19:00 - 20:35', '周五',        4, 4
) AS t(slot, name, time_range, day_label, weekday, sort_order)
WHERE NOT EXISTS (SELECT 1 FROM `periods` p WHERE p.slot = t.slot);

-- ============================================================
--  4. 课程资料（RAG 检索数据源）
-- ============================================================
INSERT INTO `course_materials` (`course`, `code`, `docs`, `focus`)
SELECT * FROM (
  SELECT '操作系统原理', 'COMP3011',
         '《Operating Systems: Three Easy Pieces》讲义 PDF、xv6 实验手册 v2.4',
         '进程调度算法（MLFQ）、虚拟内存页表转换、死锁四个必要条件与银行家算法、文件系统 Inode 结构。'
  UNION ALL SELECT '深度学习导论', 'AINT3050',
         'PyTorch 算子实战讲义、反向传播推导笔记、Transformer 论文精读 PPT',
         '梯度消失与残差连接（ResNet）、BatchNorm 原理、Self-Attention 矩阵缩放点积计算、Adam 优化器公式。'
  UNION ALL SELECT '计算机网络', 'COMP3042',
         '《计算机网络：自顶向下方法》第8版课件、Wireshark 抓包实验指导书',
         'TCP 三次握手与四次挥手状态机、拥塞控制（慢开始/拥塞避免/快重传）、OSPF 与 BGP 路由协议对比。'
  UNION ALL SELECT '数据库系统概论', 'COMP3080',
         'SQL 优化实验文档、B+ 树索引源码剖析、事务 ACID 与 MVCC 讲义',
         'BCNF 范式分解、B+ 树聚簇索引与非聚簇索引、两阶段锁协议 (2PL)、Redo/Undo 日志恢复机制。'
  UNION ALL SELECT '大模型与智能体开发', 'AINT3120',
         'Spring AI / LangChain4j 实战手册、ReAct 论文与 Tool Calling 接口规范',
         'Prompt 工程、RAG 向量切片与混合检索、Function Calling 工具注册、记忆管理 (ChatMemory)。'
  UNION ALL SELECT '高等工程数学', 'MATH2001',
         '《高等数学》同济第七版上下册、习题全解、期末模拟卷三套',
         '极限与连续、导数与微分、级数收敛性判别法、多重积分与格林公式。'
  UNION ALL SELECT '软件工程导论', 'SE1001',
         '《软件工程导论》课程讲义、需求分析模板、用例建模实验指导',
         '需求获取与建模、软件过程模型（瀑布/增量/敏捷）、软件测试黑盒与白盒方法。'
) AS t(course, code, docs, focus)
WHERE NOT EXISTS (SELECT 1 FROM `course_materials` m WHERE m.course = t.course);

-- ============================================================
--  5. 课表数据
--     user_id 通过子查询按用户名自动匹配
-- ============================================================

-- 5.1 用户 aaa（小黑）：8 门
INSERT INTO `schedule_items`
  (`user_id`,`day`,`slot`,`time_range`,`course_name`,`teacher`,`room`,`weeks`,`color`,`material_key`)
SELECT u.id, s.day, s.slot, s.time_range, s.course_name, s.teacher, s.room, s.weeks, s.color, s.material_key
FROM `users` u
JOIN (
  SELECT 1 AS day, 1 AS slot, '08:00 - 09:35' AS time_range, '高等工程数学' AS course_name, '周明远 教授' AS teacher, '一教 A203' AS room, '1-16周' AS weeks, 'blue' AS color, '高数' AS material_key
  UNION ALL SELECT 1,2,'10:00 - 11:35','操作系统原理','陈振华 教授','信息楼 B302','1-16周','emerald','操作系统'
  UNION ALL SELECT 1,3,'14:00 - 15:35','深度学习导论','沈逸飞 副教授','智算中心 104','1-16周','purple','深度学习'
  UNION ALL SELECT 2,2,'10:00 - 11:35','计算机网络','周敏 副教授','信息楼 A208','1-16周','amber','计算机网络'
  UNION ALL SELECT 3,1,'08:00 - 09:35','操作系统原理 (实验)','陈振华 教授','机房 C401','2-16双周','emerald','操作系统'
  UNION ALL SELECT 3,3,'14:00 - 15:35','数据库系统概论','刘志远 教授','信息楼 A405','1-16周','rose','数据库'
  UNION ALL SELECT 4,2,'10:00 - 11:35','深度学习导论','沈逸飞 副教授','智算中心 104','1-16周','purple','深度学习'
  UNION ALL SELECT 5,2,'10:00 - 11:35','大模型与智能体开发','林牧 副教授','智算中心 204','1-12周','indigo','智能体'
) s
WHERE u.username = 'aaa'
  AND NOT EXISTS (
    SELECT 1 FROM `schedule_items` e WHERE e.user_id = u.id AND e.day = s.day AND e.slot = s.slot
  );

-- 5.2 用户 dawg：5 门（周一 3 门，保证"今日课表"有内容）
INSERT INTO `schedule_items`
  (`user_id`,`day`,`slot`,`time_range`,`course_name`,`teacher`,`room`,`weeks`,`color`,`material_key`)
SELECT u.id, s.day, s.slot, s.time_range, s.course_name, s.teacher, s.room, s.weeks, s.color, s.material_key
FROM `users` u
JOIN (
  SELECT 1 AS day, 1 AS slot, '08:00 - 09:35' AS time_range, '高等工程数学' AS course_name, '周明远 教授' AS teacher, '一教 A203' AS room, '1-16周' AS weeks, 'blue' AS color, '高数' AS material_key
  UNION ALL SELECT 1,2,'10:00 - 11:35','操作系统原理','陈振华 教授','信息楼 B302','1-16周','emerald','操作系统'
  UNION ALL SELECT 1,3,'14:00 - 15:35','深度学习导论','沈逸飞 副教授','智算中心 104','1-16周','purple','深度学习'
  UNION ALL SELECT 3,2,'10:00 - 11:35','计算机网络','周敏 副教授','信息楼 A208','1-16周','amber','计算机网络'
  UNION ALL SELECT 4,3,'14:00 - 15:35','数据库系统概论','刘志远 教授','信息楼 A405','1-16周','rose','数据库'
) s
WHERE u.username = 'dawg'
  AND NOT EXISTS (
    SELECT 1 FROM `schedule_items` e WHERE e.user_id = u.id AND e.day = s.day AND e.slot = s.slot
  );

-- 5.3 用户 bbb（小林）：3 门
INSERT INTO `schedule_items`
  (`user_id`,`day`,`slot`,`time_range`,`course_name`,`teacher`,`room`,`weeks`,`color`,`material_key`)
SELECT u.id, s.day, s.slot, s.time_range, s.course_name, s.teacher, s.room, s.weeks, s.color, s.material_key
FROM `users` u
JOIN (
  SELECT 1 AS day, 2 AS slot, '10:00 - 11:35' AS time_range, '软件工程导论' AS course_name, '吴建国 教授' AS teacher, '软院楼 102' AS room, '1-16周' AS weeks, 'blue' AS color, '软件工程' AS material_key
  UNION ALL SELECT 1,4,'16:00 - 17:35','Web前端架构设计','林晓 讲师','软院楼 305','1-16周','emerald','前端'
  UNION ALL SELECT 3,2,'10:00 - 11:35','数据库系统概论','刘志远 教授','信息楼 A405','1-16周','rose','数据库'
) s
WHERE u.username = 'bbb'
  AND NOT EXISTS (
    SELECT 1 FROM `schedule_items` e WHERE e.user_id = u.id AND e.day = s.day AND e.slot = s.slot
  );

-- 5.4 用户 ccc（小周）：4 门
INSERT INTO `schedule_items`
  (`user_id`,`day`,`slot`,`time_range`,`course_name`,`teacher`,`room`,`weeks`,`color`,`material_key`)
SELECT u.id, s.day, s.slot, s.time_range, s.course_name, s.teacher, s.room, s.weeks, s.color, s.material_key
FROM `users` u
JOIN (
  SELECT 1 AS day, 1 AS slot, '08:00 - 09:35' AS time_range, '深度学习导论' AS course_name, '沈逸飞 副教授' AS teacher, '智算中心 104' AS room, '1-16周' AS weeks, 'purple' AS color, '深度学习' AS material_key
  UNION ALL SELECT 2,3,'14:00 - 15:35','数据库系统概论','刘志远 教授','信息楼 A405','1-16周','rose','数据库'
  UNION ALL SELECT 3,1,'08:00 - 09:35','大模型与智能体开发','林牧 副教授','智算中心 204','1-12周','indigo','智能体'
  UNION ALL SELECT 5,2,'10:00 - 11:35','计算机网络','周敏 副教授','信息楼 A208','1-16周','amber','计算机网络'
) s
WHERE u.username = 'ccc'
  AND NOT EXISTS (
    SELECT 1 FROM `schedule_items` e WHERE e.user_id = u.id AND e.day = s.day AND e.slot = s.slot
  );

-- ============================================================
--  6. 学习计划
-- ============================================================
INSERT INTO `study_plans` (`user_id`,`title`,`plan_type`,`status`,`items`,`raw_draft`)
SELECT u.id, p.title, p.plan_type, p.status, p.items, ''
FROM `users` u
JOIN (
  SELECT 'aaa' AS username, '《操作系统原理》第5周课前预习计划' AS title, '预习计划' AS plan_type, '进行中' AS status,
         JSON_ARRAY(
           '通读教材第 18-20 章：分页机制与多级页表设计（约 45 分钟）',
           '理解 TLB（快表）未命中时的硬件与操作系统处理流程',
           '运行 xv6 Lab2 分页实验环境，阅读 vm.c 核心函数源码'
         ) AS items
  UNION ALL SELECT 'aaa', '《计算机网络》期中复习冲刺计划', '复习计划', '进行中',
         JSON_ARRAY(
           '整理传输层 UDP 与 TCP 报文首部字段对比思维导图',
           '重做第 3 章课后计算题：序号、确认号与滑动窗口大小计算',
           '复盘 Wireshark 实验二：分析 HTTP 与 TCP 拥塞窗口变化曲线'
         )
  UNION ALL SELECT 'aaa', '《大模型与智能体开发》校园课程助手项目实践计划', '预习计划', '已完成',
         JSON_ARRAY(
           '熟悉课表查询 Tool、课程资料检索 Tool 与学习计划保存 Tool 的参数定义',
           '测试多轮对话上下文记忆：先生成草稿计划，用户确认说「保存」再触发入库'
         )
  UNION ALL SELECT 'dawg', '《操作系统原理》课堂笔记整理计划', '复习计划', '进行中',
         JSON_ARRAY(
           '整理第 3-4 节课堂笔记：进程控制块 PCB 结构与上下文切换流程',
           '完成 Pytorch 张量广播与自动求导练习题',
           '预习《计算机网络》第 3-4 节：TCP 流量控制与滑动窗口协议'
         )
  UNION ALL SELECT 'dawg', '《计算机网络》期末冲刺计划', '复习计划', '进行中',
         JSON_ARRAY(
           '绘制 TCP 三次握手与四次挥手完整状态机图',
           '默写拥塞控制四个阶段的 cwnd 变化曲线',
           '限时完成两套综合模拟卷并订正'
         )
  UNION ALL SELECT 'bbb', '《软件工程导论》需求建模预习计划', '预习计划', '进行中',
         JSON_ARRAY(
           '学习 UML 用例图与活动图绘制规范',
           '完成需求分析实验一：写出图书管理系统用例描述'
         )
) p
WHERE u.username = p.username
  AND NOT EXISTS (SELECT 1 FROM `study_plans` e WHERE e.user_id = u.id AND e.title = p.title);

-- ============================================================
--  7. 清理测试用会话记录
-- ------------------------------------------------------------
-- 如需保留历史对话，注释掉下面这行
-- ============================================================
DELETE FROM `chat_sessions`;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
--  查询验证
-- ============================================================
SELECT 'users'            AS 表名, COUNT(*) AS 记录数 FROM `users`         UNION ALL
SELECT 'terms',                  COUNT(*)          FROM `terms`          UNION ALL
SELECT 'periods',                COUNT(*)          FROM `periods`        UNION ALL
SELECT 'course_materials',       COUNT(*)          FROM `course_materials` UNION ALL
SELECT 'schedule_items',         COUNT(*)          FROM `schedule_items` UNION ALL
SELECT 'study_plans',            COUNT(*)          FROM `study_plans`;

-- 各账号课表数量
SELECT u.username, u.nickname, u.major,
       (SELECT COUNT(*) FROM `schedule_items` s WHERE s.user_id = u.id) AS 课表数,
       (SELECT COUNT(*) FROM `study_plans`   p WHERE p.user_id = u.id) AS 计划数
FROM `users` u ORDER BY u.id;