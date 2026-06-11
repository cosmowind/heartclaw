# HeartClaw Credits 体系重构报告

## 重构概述

已成功将 HeartClaw 的经济体系从 token 为中心重构为 credits 为中心，使系统更直观、更易于理解。

## 核心概念

**1 credit = 1 次对话或 1 次 API 调用**

- 每天自动领取 10 credits
- 每次自迭代对话消耗 1 credit
- Token 预算基于对话次数计算：每次对话约消耗 3000 tokens

## 重构内容

### 1. Credits 体系重新设计

**文件**: `/www/wwwroot/projects/heartclaw/data/routine/credits.json`

**新结构**:
```json
{
  "credits": {
    "daily_claim": 10,
    "claimed_today": false,
    "last_claim_date": null,
    "description": "每天自动领取 10 credits，用于自迭代对话"
  },
  "token_budget": {
    "daily_budget": 33000,
    "token_price": 0.02,
    "description": "Token 预算：每次对话约消耗 3000 tokens"
  }
}
```

**变更说明**:
- 移除 `auto_claim` 字段，改为 `credits` 字段
- 添加 `claimed_today` 标志，避免重复领取
- 将 token 预算独立为 `token_budget` 字段
- 明确 credits 和 token 的关系

### 2. 每日流程更新

**文件**: `/www/wwwroot/projects/heartclaw/data/routine/ROUTINE.md`

**更新内容**:
- 添加"核心概念：Credits 体系"章节
- 更新"早餐"环节，说明 credits 领取和 token 预算计算
- 更新"睡前"环节，说明 credits 消耗和重置逻辑

### 3. Cron 任务更新

**Job ID**: 31e30528a967
**Schedule**: 每天 9:00

**新增功能**:
- 明确说明 1 credit = 1 次对话或 API 调用
- 自动领取 10 credits
- 创建 self-iteration Channel
- 执行 10 次自迭代对话（消耗 10 credits）
- 记录对话结果到 today_log.md
- 在睡前环节更新 credits 余额

### 4. Skill 文档更新

**Skill**: heartclaw-development

**新增内容**:
- Credits 体系详细说明
- Token 预算计算方法
- 自迭代对话消耗说明

## 测试结果

### 1. Credits 领取测试

```
当前 credits 状态:
  余额: 590
  credits: {'daily_claim': 10, 'claimed_today': False, 'last_claim_date': None, 'description': '每天自动领取 10 credits，用于自迭代对话'}

今天: 2026-06-07
上次领取: None

✅ 成功领取 10 credits
  余额变化: 590 → 600
  历史记录已更新
```

### 2. 自迭代对话测试

```
🧪 简化测试自迭代对话机制
==================================================
✅ API 状态: ok
📋 Channel 数量: 5
✅ 找到 self-iteration Channel: a9905119-ad6b-4dbc-9606-949534ca7b03

💬 发送测试消息到 Channel a9905119-ad6b-4dbc-9606-949534ca7b03...
✅ 消息发送成功
🔄 触发系统处理...
✅ 处理完成: 处理了 5 个 Channel

📚 获取消息历史...
  总消息数: 8

✅ 测试完成
```

## 使用说明

### Credits 领取

每天 9:00 cron 任务自动执行时，系统会：

1. 检查 `credits.claimed_today` 是否为 false
2. 如果为 false，则领取 10 credits
3. 更新余额和历史记录
4. 设置 `claimed_today = true`

### Token 预算计算

在"早餐"环节，系统会：

1. 获取可用 credits = current_balance
2. 计算今日 token 预算 = 可用 credits × 3000
3. 更新 `token_budget.daily_budget`

### 自迭代对话

在"今日探索"环节，系统会：

1. 创建或查找 "self-iteration" Channel
2. 发送 10 条自我对话消息
3. 每条消息消耗 1 credit
4. 每次对话后调用 `POST http://localhost:18765/wake` 触发处理
5. 记录对话结果到 `today_log.md`

### Credits 消耗

在"睡前"环节，系统会：

1. 计算今天的消耗：10 次对话 = 10 credits
2. 更新 `current_balance = current_balance - 10`
3. 重置 `credits.claimed_today = false`（为明天做准备）

## 技术细节

### Credits 领取逻辑

```python
# 检查是否需要领取
if not credits["credits"]["claimed_today"]:
    # 执行领取
    balance_before = credits["current_balance"]
    claim_amount = credits["credits"]["daily_claim"]
    balance_after = balance_before + claim_amount
    
    # 更新余额
    credits["current_balance"] = balance_after
    
    # 更新领取状态
    credits["credits"]["claimed_today"] = True
    credits["credits"]["last_claim_date"] = today
    
    # 添加历史记录
    credits["history"].append({
        "date": today,
        "action": "auto_claim",
        "credits_added": claim_amount,
        "balance_before": balance_before,
        "balance_after": balance_after
    })
```

### Token 预算计算

```python
# 计算今日 token 预算
available_credits = credits["current_balance"]
tokens_per_conversation = 3000
daily_token_budget = available_credits * tokens_per_conversation

# 更新 token 预算
credits["token_budget"]["daily_budget"] = daily_token_budget
```

### Credits 消耗逻辑

```python
# 在睡前环节
conversations_today = 10  # 固定的自迭代对话次数
credits_consumed = conversations_today  # 1 credit = 1 次对话

# 更新余额
credits["current_balance"] -= credits_consumed

# 重置领取状态（为明天做准备）
credits["credits"]["claimed_today"] = False
```

## 优势

1. **直观易懂**: 1 credit = 1 次对话，概念清晰
2. **易于管理**: 每天固定领取 10 credits，消耗 10 credits
3. **预算可控**: Token 预算基于对话次数计算，易于规划
4. **自动重置**: 每天自动领取，自动重置状态

## 后续优化

1. **动态调整**: 根据对话质量动态调整 credits 消耗
2. **奖励机制**: 完成高质量对话可获得额外 credits
3. **经验积累**: 将对话中的有价值内容整合到经验库
4. **知识管理**: 将探索的新知识添加到概念树

## 总结

已成功将 HeartClaw 的经济体系从 token 为中心重构为 credits 为中心。新体系更直观、更易于管理，每天自动领取 10 credits，用于自迭代对话，每次对话消耗 1 credit，Token 预算基于对话次数计算。
