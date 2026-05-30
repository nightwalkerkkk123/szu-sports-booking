"""
步骤构建器 - 支持重试和错误处理的流程执行
"""
from typing import Callable, Optional, List
from .chain_builder import Chain
from playwright.sync_api import Page


class StepBuilder:
    """
    分步骤构建选择流程，每步可配置重试次数、超时等

    示例:
        StepBuilder(page) \\
            .step("选择校区").click("粤海校区") \\
            .step("选择项目").click("网球") \\
            .run()
    """

    def __init__(self, page: Page):
        self.page = page
        self.steps = []
        self.chain = Chain(page)

    def step(self, description: str) -> "StepBuilder":
        """
        定义一个步骤

        参数:
            description: 步骤描述，用于日志输出
        """
        self.steps.append({
            "description": description,
            "retries": 3,
            "delay": 0,
            "action": None,
            "on_error": None,
        })
        return self

    def click(
        self,
        target: str = None,
        *,
        index: int = None,
        contains: str = None,
        timeout: int = 10000
    ) -> "StepBuilder":
        """
        点击目标

        参数:
            target: 精确匹配的文本
            index: 按索引选择
            contains: 包含文本匹配
            timeout: 超时时间(ms)
        """
        self.steps[-1]["action"] = ("click", {
            "target": target,
            "index": index,
            "contains": contains,
            "timeout": timeout
        })
        return self

    def click_first(self) -> "StepBuilder":
        """点击第一个可用元素"""
        self.steps[-1]["action"] = ("click_first", {})
        return self

    def wait(self, seconds: float) -> "StepBuilder":
        """等待秒数"""
        self.steps[-1]["action"] = ("wait", seconds)
        return self

    def wait_for(self, selector: str, timeout: int = 10000) -> "StepBuilder":
        """等待元素出现"""
        self.steps[-1]["action"] = ("wait_for", {"selector": selector, "timeout": timeout})
        return self

    def retries(self, count: int) -> "StepBuilder":
        """设置重试次数"""
        self.steps[-1]["retries"] = count
        return self

    def delay(self, seconds: float) -> "StepBuilder":
        """步骤之间延迟"""
        self.steps[-1]["delay"] = seconds
        return self

    def on_error(self, callback: Callable) -> "StepBuilder":
        """错误处理回调"""
        self.steps[-1]["on_error"] = callback
        return self

    def run(self, stop_on_error: bool = False) -> bool:
        """
        执行所有步骤

        参数:
            stop_on_error: 遇到错误是否停止

        返回:
            bool: 所有步骤是否成功
        """
        print("\n" + "=" * 50)
        print("开始执行步骤...")
        print("=" * 50 + "\n")

        for i, step in enumerate(self.steps):
            desc = step["description"]
            retries = step.get("retries", 1)
            delay = step.get("delay", 0)

            print(f"[步骤 {i+1}/{len(self.steps)}] {desc}")

            success = False
            last_error = None

            for attempt in range(retries):
                try:
                    action = step.get("action")
                    if action is None:
                        print(f"  (无操作，跳过)")
                        success = True
                        break

                    action_type, action_data = action

                    if action_type == "click":
                        self.chain.click(
                            target=action_data.get("target"),
                            index=action_data.get("index"),
                            contains=action_data.get("contains"),
                            timeout=action_data.get("timeout", 10000)
                        )
                        success = True

                    elif action_type == "click_first":
                        self.chain.click_first()
                        success = True

                    elif action_type == "wait":
                        import time
                        time.sleep(action_data)
                        success = True

                    elif action_type == "wait_for":
                        self.chain.wait_for(
                            action_data["selector"],
                            action_data.get("timeout", 10000)
                        )
                        success = True

                    if success:
                        print(f"  [OK] 成功")
                        break

                except Exception as e:
                    last_error = e
                    if attempt < retries - 1:
                        print(f"  ! 第 {attempt + 1} 次失败，重试中... ({e})")
                    else:
                        print(f"  [X] 失败: {e}")

            if not success and stop_on_error:
                return False

            if delay > 0:
                import time
                time.sleep(delay)

        print("\n" + "=" * 50)
        print("步骤执行完成")
        print("=" * 50 + "\n")

        return True

    def get_history(self) -> List[tuple]:
        """获取操作历史"""
        return self.chain.history