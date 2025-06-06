from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
import time
import cv2


@AgentServer.custom_action("GetKeyFromHole_Test")
class GetKeyFromHole_Test(CustomAction):
    # 这里检查钥匙是否可以自动获取
    def get_distance_from_key_to_target(self, context: Context):

        distance = 0

        img = context.tasker.controller.post_screencap().wait().get()
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary_img = cv2.threshold(gray_img, 40, 255, cv2.THRESH_BINARY)

        # 初始化结果列表
        pixel_counts = []
        roi_list = []
        result_list = []

        # 从右向左遍历，每次左移5个像素
        for i in range(0, 640, 5):
            # 计算当前矩形区域坐标
            x = max(35, 640 - i - 60)  # 确保不超过指定边界
            y = 575  # 指定位置为绳子坐标
            w = 60
            h = 45

            # 确保矩形不超过指定边界
            if x - w < 35:
                w = 20 - x

            # 跳过无效的矩形区域
            if w <= 0 or h <= 0:
                continue

            # 提取矩形区域
            roi = binary_img[y : y + h, x - w : x]

            # 统计白色像素点 (255)
            count = cv2.countNonZero(roi)
            pixel_counts.append(count)
            roi_list.append([x, y, w, h])

        for i in range(1, len(pixel_counts) - 1):
            if pixel_counts[i] <= 1900 and pixel_counts[i - 1] > 1900:
                result_list.append(roi_list[i])
                x, y, w, h = roi_list[i]

        if len(result_list) != 2:
            return distance
        elif result_list[0][0] >= 500:
            return distance
        else:
            distance = abs(result_list[0][0] - result_list[1][0])
            print("distance: ", distance, "roi: ", result_list)
            return distance

    #  两个ROI之间的距离需要优化，拉绳子的步长需要优化
    # distance:  325 roi:  [[470, 575, 60, 45], [145, 575, 60, 45]]
    # distance:  200 roi:  [[445, 575, 60, 45], [245, 575, 60, 45]]
    # distance:  250 roi:  [[440, 575, 60, 45], [190, 575, 60, 45]]
    # distance:  255 roi:  [[410, 575, 60, 45], [155, 575, 60, 45]]
    # distance:  240 roi:  [[435, 575, 60, 45], [195, 575, 60, 45]]
    # 执行函数
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        context.run_task("FindKeyHole")
        distance = self.get_distance_from_key_to_target(context)
        while distance == 0 or distance < 200:
            context.run_task("BackText")
            context.run_task("FindKeyHole")
            distance = self.get_distance_from_key_to_target(context)

        print(distance, "如果distance为0或者distance小于200则说明很大概率获取不到钥匙")
        findleftstringdetail = context.run_task("FindLeftString")
        if findleftstringdetail:
            leftstringstart = findleftstringdetail.nodes[0].recognition.box.x
        print("leftstringstart:", leftstringstart)

        # 按下button开始移动钥匙，同时检测钥匙是否到达合适位置，即当前检测到的位置
        # x - leftstringstart = distance
        button_x = 105
        button_y = 795
        now_leftstring = leftstringstart
        while now_leftstring < leftstringstart + distance:
            print("now_leftstring: " + str(now_leftstring))

            remaining_distance = leftstringstart + distance - now_leftstring
            if remaining_distance < 5:  # 容差范围
                break
            elif remaining_distance > 200:
                step = 80  # 远距离大步长
            elif remaining_distance > 50:
                step = 30  # 中距离中等步长
            else:
                step = 10  # 近距离微调

            # 移动按钮
            context.tasker.controller.post_swipe(
                button_x, button_y, button_x + step, button_y, 100
            )
            now_leftstring = (
                context.run_task("FindLeftString").nodes[0].recognition.box.x
            )
            print("move button ", step)
            # 记录按钮位置
            button_x += step

        context.run_task("ClickConfirmForKey")
        time.sleep(3)

        img = context.tasker.controller.post_screencap().wait().get()
        if context.run_recognition("Fight_ClosedDoor", img):
            return CustomAction.RunResult(success=False)
        else:
            return CustomAction.RunResult(success=True)
