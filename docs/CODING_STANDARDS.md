# 代码规范

> **文档路径**: `/www/wwwroot/projects/heart/docs/CODING_STANDARDS.md`
> **基于**: WCS-CN v1
> **更新日期**: 2026-05-09

---

## 通用规则

1. **类型注解**: 所有函数和类方法必须有类型注解
2. **异步优先**: 心跳项目基于 asyncio，全部 I/O 操作必须使用 `async/await`
3. **单一职责**: 每个模块只做一件事
4. **避免硬编码**: 配置值外置到函数参数或配置文件

## 命名约定

| 类型 | 约定 | 示例 |
|---|---|---|
| 类名 | PascalCase | `ChainContext`, `Lobster` |
| 函数/方法 | snake_case | `add_task`, `execute_chain` |
| 常量 | UPPER_SNAKE_CASE | `DEFAULT_INTERVAL` |
| 私有属性 | `_single_leading` | `_task`, `_queue` |

## 模块导入顺序

1. 标准库
2. 第三方库
3. 本项目模块
4. 相对导入使用 `.` 前缀

## 文档字符串

- 所有模块、类、公共函数使用 docstring
- Google 风格（`"""描述\n\nArgs:\n    ...\nReturns:\n    ...\n"""`）

## 测试策略

- 每个模块对应一个 `test_<module>.py`
- 使用 `pytest` + `pytest-asyncio`
- 测试文件放在 `tests/` 目录（与 `docs/` 同级）

## 提交规范

- 格式: `<type>: <简短描述>`
- type: `feat`, `fix`, `docs`, `refactor`, `test`
- 示例: `feat: 添加 ChainContext 数据类`
