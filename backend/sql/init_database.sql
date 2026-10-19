-- ============================================================
-- 校园课程智能助手 · 数据库初始化脚本
-- 数据库: campus_course_assistant
-- 字符集: utf8mb4
-- 用法: Navicat 新建查询 -> 粘贴本文件 -> 运行
-- 注意: 本脚本会 DROP 同名表后重建，数据为空，请先备份
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';

CREATE DATABASE IF NOT EXISTS `campus_course_assistant`
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `campus_course_assistant`;

-- ------------------------------------------------------------
-- 1. 用户表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `chat_sessions`;
DROP TABLE IF EXISTS `study_plans`;
DROP TABLE IF EXISTS `schedule_items`;
DROP TABLE IF EXISTS `course_materials`;
DROP TABLE IF EXISTS `periods`;
DROP TABLE IF EXISTS `terms`;
DROP TABLE IF EXISTS `users`;

CREATE TABLE `users` (
  `id`            INT           NOT NULL AUTO_INCREMENT COMMENT '主键',
  `username`      VARCHAR(64)   NOT NULL COMMENT '登录用户名',
  `nickname`      VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '学生姓名/昵称',
  `major`         VARCHAR(128)  NOT NULL DEFAULT '' COMMENT '专业',
  `grade`         VARCHAR(32)   NOT NULL DEFAULT '' COMMENT '年级',
  `role`          VARCHAR(16)   NOT NULL DEFAULT 'student' COMMENT '角色 student/admin，admin 可查看他人课表',
  `hashed_password` VARCHAR(255) NOT NULL COMMENT 'bcrypt 密码哈希',
  `created_at`    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_username` (`username`),
  KEY `ix_users_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生用户表';

-- ------------------------------------------------------------
-- 2. 学年学期表
-- ------------------------------------------------------------
CREATE TABLE `terms` (
  `id`         INT         NOT NULL AUTO_INCREMENT COMMENT '主键',
  `label`      VARCHAR(64) NOT NULL COMMENT '学期名称',
  `is_current` TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '是否为当前学期',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_terms_label` (`label`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学年学期表';

-- ------------------------------------------------------------
-- 3. 作息节次表（课表格子数据）
-- ------------------------------------------------------------
CREATE TABLE `periods` (
  `id`         INT         NOT NULL AUTO_INCREMENT COMMENT '主键',
  `slot`       INT         NOT NULL COMMENT '第几节次',
  `name`       VARCHAR(64) NOT NULL COMMENT '节次名称，如 第 1-2 节',
  `time_range` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '上课时间段',
  `day_label`  VARCHAR(64) NOT NULL DEFAULT '' COMMENT '星期列标题',
  `weekday`    INT         NOT NULL DEFAULT 0 COMMENT '0=周一 1=周二 ... 4=周五',
  `sort_order` INT         NOT NULL DEFAULT 0 COMMENT '排序号',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_periods_slot` (`slot`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作息节次表';

-- ------------------------------------------------------------
-- 4. 课程表
-- ------------------------------------------------------------
CREATE TABLE `schedule_items` (
  `id`          INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`     INT          NOT NULL COMMENT '所属用户',
  `day`         INT          NOT NULL COMMENT '1=周一 ... 5=周五',
  `slot`        INT          NOT NULL COMMENT '第几节次',
  `time_range`  VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '上课时间段',
  `course_name` VARCHAR(128) NOT NULL COMMENT '课程名称',
  `teacher`     VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '任课教师',
  `room`        VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '上课地点',
  `weeks`       VARCHAR(64)  NOT NULL DEFAULT '1-16周' COMMENT '开课周次',
  `color`       VARCHAR(32)  NOT NULL DEFAULT 'blue' COMMENT '前端卡片配色',
  `material_key` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '关联课程资料关键词',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_schedule_slot` (`user_id`, `day`, `slot`),
  KEY `ix_schedule_items_user_id` (`user_id`),
  CONSTRAINT `fk_schedule_items_user` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生课表表';

-- ------------------------------------------------------------
-- 5. 课程资料表（RAG 数据源）
-- ------------------------------------------------------------
CREATE TABLE `course_materials` (
  `id`     INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
  `course` VARCHAR(128) NOT NULL COMMENT '课程名称',
  `code`   VARCHAR(32)  NOT NULL DEFAULT '' COMMENT '课程代码',
  `docs`   TEXT         NOT NULL COMMENT '教材与实验资料',
  `focus`  TEXT         NOT NULL COMMENT '核心考点与复习重点',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_course_materials_course` (`course`),
  KEY `ix_course_materials_course` (`course`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程资料表(RAG数据源)';

-- ------------------------------------------------------------
-- 6. 学习计划表
-- ------------------------------------------------------------
CREATE TABLE `study_plans` (
  `id`         INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`    INT          NOT NULL COMMENT '所属用户',
  `title`      VARCHAR(255) NOT NULL COMMENT '计划标题',
  `plan_type`  VARCHAR(32)  NOT NULL DEFAULT '复习计划' COMMENT '预习计划/复习计划',
  `status`     VARCHAR(32)  NOT NULL DEFAULT '进行中' COMMENT '计划状态',
  `items`      JSON         NOT NULL COMMENT '计划条目数组',
  `raw_draft`  TEXT         NOT NULL COMMENT '计划原始草稿',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `ix_study_plans_user_id` (`user_id`),
  CONSTRAINT `fk_study_plans_user` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学习计划表';

-- ------------------------------------------------------------
-- 7. 对话会话表
-- ------------------------------------------------------------
CREATE TABLE `chat_sessions` (
  `id`         INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id`    INT          NOT NULL COMMENT '所属用户',
  `title`      VARCHAR(255) NOT NULL DEFAULT '新的对话' COMMENT '会话标题',
  `history`    JSON         NOT NULL COMMENT '消息历史数组',
  `is_active`  TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '是否活跃',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `ix_chat_sessions_user_id` (`user_id`),
  CONSTRAINT `fk_chat_sessions_user` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话会话表';

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
--                    初始化数据
-- ============================================================

-- ------------------------------------------------------------
-- 学年学期（供前端课表页标题读取）
-- ------------------------------------------------------------
INSERT INTO `terms` (`label`, `is_current`) VALUES
('2026-2027学年 第一学期', 1);

-- ------------------------------------------------------------
-- 作息节次（供前端课表格子读取）
-- ------------------------------------------------------------
INSERT INTO `periods` (`slot`, `name`, `time_range`, `day_label`, `weekday`, `sort_order`) VALUES
(1, '第 1-2 节', '08:00 - 09:35', '周一 (今天)', 0, 0),
(2, '第 3-4 节', '10:00 - 11:35', '周二',        1, 1),
(3, '第 5-6 节', '14:00 - 15:35', '周三',        2, 2),
(4, '第 7-8 节', '16:00 - 17:35', '周四',        3, 3),
(5, '第 9-10 节', '19:00 - 20:35', '周五',       4, 4);

-- ------------------------------------------------------------
-- 用户（密码均为 123456，bcrypt 哈希请勿改动）
--   aaa -> 小黑 / 计算机科学与技术 / 大三（管理员 role=admin）
--   bbb -> 小林 / 软件工程 / 大二
-- 注：以下哈希对应公开演示账号（123456），属测试数据，非真实凭据。
--     需要更多演示账号请使用 backend/sql/init_data.sql（幂等脚本）。
-- ------------------------------------------------------------
INSERT INTO `users` (`username`, `nickname`, `major`, `grade`, `role`, `hashed_password`) VALUES
('aaa', '小黑', '计算机科学与技术', '大三', 'admin',
 '$2b$12$HouRt9mvC4SFJJU1T9uBV.ln4V1ObT95jkKpXABut4bAB43BUH56e'),
('bbb', '小林', '软件工程', '大二', 'student',
 '$2b$12$9fs9WhQN0x1KJ5NadeaOt.XrACwmJGTqu0Z92j2adhCqyPLnNmZ8O');

-- ------------------------------------------------------------
-- 课表：用户 aaa（小黑）
-- ------------------------------------------------------------
INSERT INTO `schedule_items`
  (`user_id`, `day`, `slot`, `time_range`, `course_name`, `teacher`, `room`, `weeks`, `color`, `material_key`) VALUES
(1, 1, 1, '08:00 - 09:35', '高等工程数学',       '周明远 教授',   '一教 A203',    '1-16周',    'blue',    '高数'),
(1, 1, 2, '10:00 - 11:35', '操作系统原理',       '陈振华 教授',   '信息楼 B302',  '1-16周',    'emerald', '操作系统'),
(1, 1, 3, '14:00 - 15:35', '深度学习导论',       '沈逸飞 副教授', '智算中心 104', '1-16周',    'purple',  '深度学习'),
(1, 2, 2, '10:00 - 11:35', '计算机网络',         '周敏 副教授',   '信息楼 A208',  '1-16周',    'amber',   '计算机网络'),
(1, 3, 1, '08:00 - 09:35', '操作系统原理 (实验)', '陈振华 教授',   '机房 C401',    '2-16双周',  'emerald', '操作系统'),
(1, 3, 3, '14:00 - 15:35', '数据库系统概论',     '刘志远 教授',   '信息楼 A405',  '1-16周',    'rose',    '数据库'),
(1, 4, 2, '10:00 - 11:35', '深度学习导论',       '沈逸飞 副教授', '智算中心 104', '1-16周',    'purple',  '深度学习'),
(1, 5, 2, '10:00 - 11:35', '大模型与智能体开发', '林牧 副教授',   '智算中心 204', '1-12周',    'indigo',  '智能体');

-- ------------------------------------------------------------
-- 课表：用户 bbb（小林）
-- ------------------------------------------------------------
INSERT INTO `schedule_items`
  (`user_id`, `day`, `slot`, `time_range`, `course_name`, `teacher`, `room`, `weeks`, `color`, `material_key`) VALUES
(2, 1, 2, '10:00 - 11:35', '软件工程导论',   '吴建国 教授', '软院楼 102', '1-16周', 'blue',    '软件工程'),
(2, 1, 4, '16:00 - 17:35', 'Web前端架构设计', '林晓 讲师',   '软院楼 305', '1-16周', 'emerald', '前端'),
(2, 3, 2, '10:00 - 11:35', '数据库系统概论', '刘志远 教授', '信息楼 A405', '1-16周', 'rose',    '数据库');

-- ------------------------------------------------------------
-- 课程资料（RAG 检索数据源）
-- ------------------------------------------------------------
INSERT INTO `course_materials` (`course`, `code`, `docs`, `focus`) VALUES
('操作系统原理', 'COMP3011',
 '《Operating Systems: Three Easy Pieces》讲义 PDF、xv6 实验手册 v2.4',
 '进程调度算法（MLFQ）、虚拟内存页表转换、死锁四个必要条件与银行家算法、文件系统 Inode 结构。'),
('深度学习导论', 'AINT3050',
 'PyTorch 算子实战讲义、反向传播推导笔记、Transformer 论文精读 PPT',
 '梯度消失与残差连接（ResNet）、BatchNorm 原理、Self-Attention 矩阵缩放点积计算、Adam 优化器公式。'),
('计算机网络', 'COMP3042',
 '《计算机网络：自顶向下方法》第8版课件、Wireshark 抓包实验指导书',
 'TCP 三次握手与四次挥手状态机、拥塞控制（慢开始/拥塞避免/快重传）、OSPF 与 BGP 路由协议对比。'),
('数据库系统概论', 'COMP3080',
 'SQL 优化实验文档、B+ 树索引源码剖析、事务 ACID 与 MVCC 讲义',
 'BCNF 范式分解、B+ 树聚簇索引与非聚簇索引、两阶段锁协议 (2PL)、Redo/Undo 日志恢复机制。'),
('大模型与智能体开发', 'AINT3120',
 'Spring AI / LangChain4j 实战手册、ReAct 论文与 Tool Calling 接口规范',
 'Prompt 工程、RAG 向量切片与混合检索、Function Calling 工具注册、记忆管理 (ChatMemory)。');

-- ------------------------------------------------------------
-- 学习计划：用户 aaa
-- ------------------------------------------------------------
INSERT INTO `study_plans` (`user_id`, `title`, `plan_type`, `status`, `items`, `raw_draft`) VALUES
(1, '《操作系统原理》第5周课前预习计划', '预习计划', '进行中',
 JSON_ARRAY(
   '通读教材第 18-20 章：分页机制与多级页表设计（约 45 分钟）',
   '理解 TLB（快表）未命中时的硬件与操作系统处理流程',
   '运行 xv6 Lab2 分页实验环境，阅读 vm.c 核心函数源码'
 ), ''),
(1, '《计算机网络》期中复习冲刺计划', '复习计划', '进行中',
 JSON_ARRAY(
   '整理传输层 UDP 与 TCP 报文首部字段对比思维导图',
   '重做第 3 章课后计算题：序号、确认号与滑动窗口大小计算',
   '复盘 Wireshark 实验二：分析 HTTP 与 TCP 拥塞窗口变化曲线'
 ), ''),
(1, '《大模型与智能体开发》校园课程助手项目实践计划', '预习计划', '已完成',
 JSON_ARRAY(
   '熟悉课表查询 Tool、课程资料检索 Tool 与学习计划保存 Tool 的参数定义',
   '测试多轮对话上下文记忆：先生成草稿计划，用户确认说「保存」再触发入库'
 ), '');

-- ============================================================
--                    查询验证
-- ============================================================
SELECT 'users'         AS 表名, COUNT(*) AS 记录数 FROM `users`         UNION ALL
SELECT 'terms',              COUNT(*)          FROM `terms`          UNION ALL
SELECT 'periods',            COUNT(*)          FROM `periods`        UNION ALL
SELECT 'schedule_items',     COUNT(*)          FROM `schedule_items` UNION ALL
SELECT 'course_materials',   COUNT(*)          FROM `course_materials` UNION ALL
SELECT 'study_plans',        COUNT(*)          FROM `study_plans`;