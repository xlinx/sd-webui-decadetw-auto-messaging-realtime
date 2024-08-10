import os
from threading import Timer

import pyautogui
import logging

import gradio as gr
from modules import scripts
from modules.processing import StableDiffusionProcessingTxt2Img
import datetime
import requests

log = logging.getLogger("[auto-messaging-realtime]")


class RepeatingTimer(Timer):
    def run(self):
        self.finished.wait(self.interval)
        while not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
            self.finished.wait(self.interval)


class AutoMessaging(scripts.Script):
    def __init__(self) -> None:
        super().__init__()

    def title(self):
        return ("Link fetcher")

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    lin_notify_history_array = []
    timer_couunt_threading = None

    # bot_line_notify_trigger_by_temperature_label = "60°C/140°F"

    def send_msg_linenotify(self, bot_line_notify_token, bot_line_notify_trigger_by,
                            bot_line_notify_trigger_by_time_count,
                            bot_line_notify_send_with, bot_line_notify_msg_header):
        log.warning(f"[][][send_msg_linenotify]: {bot_line_notify_token}")

        url = 'https://notify-api.line.me/api/notify'
        headers = {
            'Authorization': 'Bearer ' + bot_line_notify_token
        }
        msg_all = bot_line_notify_msg_header + str(bot_line_notify_trigger_by) + str(bot_line_notify_send_with)
        data = {
            'message': msg_all
        }

        if "ScreenShot" in bot_line_notify_send_with:
            myscreenshot = pyautogui.screenshot()
            base_folder = os.path.dirname(__file__)
            image_path = os.path.join(base_folder, "..", "myScreenshot.png")
            myscreenshot.save(image_path)
            image = open(image_path, 'rb')
            imagefile = {'imageFile': image}
            result = requests.post(url, headers=headers, data=data, files=imagefile)
            log.warning(f"[][][send_msg_linenotify][with screenshot]result: {result}")
        else:
            result = requests.post(url, headers=headers, data=data)
            log.warning(f"[][][send_msg_linenotify]result: {result}")

        result = str(result.text)
        self.lin_notify_history_array.append([datetime.datetime.now().__str__(), result, msg_all])
        if len(self.lin_notify_history_array) > 3:
            self.lin_notify_history_array.remove(self.lin_notify_history_array[0])

        if "Timer" in bot_line_notify_trigger_by:
            # if self.timer_couunt_threading is None:
            self.timer_couunt_threading = Timer(bot_line_notify_trigger_by_time_count, self.send_msg_linenotify,
                                                [bot_line_notify_token, bot_line_notify_trigger_by,
                                                 bot_line_notify_trigger_by_time_count,
                                                 bot_line_notify_send_with, bot_line_notify_msg_header])
            self.timer_couunt_threading.start()
        else:
            self.timer_couunt_threading.cancel()
            self.timer_couunt_threading = None
        return self.lin_notify_history_array

    def send_msg_telegram(self, msg: str, token: str, chatid: str):
        assert type(msg) == str, "must be str"
        url = f'https://api.telegram.org/bot{token}/sendMessage?chat_id={chatid}&text={msg}'
        requests.get(url)

    def update_temperature_label(self, celsius):
        fahrenheit = round((celsius * 1.8) + 32, 1)
        result = f" {celsius}°C/{fahrenheit}°F"
        log.warning(f"[][][update_temperature_label]result: {result}")
        # self.bot_line_notify_trigger_by_temperature.info = result
        return result

    def ui(self, is_img2img):
        with gr.Blocks():
            # gr.Markdown("Blocks")
            with gr.Accordion(open=True, label="Auto Messaging Realtime v20240808"):
                with gr.Tab("LINE-Notify"):
                    gr.Markdown("* send by each/every 1|5|10|15 image generated \n"
                                "* IF [XXX] then [YYY] \n"
                                "   ** XXX= image (send by each/every 1-100 image generated) \n"
                                "   ** XXX= time (send by every seconds. (0 to disable))\n"
                                "   ** XXX= PC-state (GPU)\n"
                                "   ** YYY= send text \n"
                                "   ** YYY= send image \n"
                                )
                    bot_line_notify_enabled = gr.Checkbox(label="0. Enable Auto Messaging", value=True)
                    bot_line_notify_token = gr.Textbox(label="1. [bot_line_notify_token]", lines=1,
                                                       value="",
                                                       placeholder="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                                                       )
                    bot_line_notify_trigger_by = gr.CheckboxGroup(["Image", "Timer", "State"],
                                                                  label="2. IF [[[ XXX ]]] Then YYY",
                                                                  info="trigger events by XXX?")
                    with gr.Row():
                        bot_line_notify_trigger_by_image_count = gr.Slider(1, 100, value=1, label="2.1 Image Count",
                                                                           step=1,
                                                                           info="send by each/every 1-100 image generated")
                        bot_line_notify_trigger_by_time_count = gr.Slider(0, 6000, value=0, label="2.2 Timer Countdown",
                                                                          step=1,
                                                                          info="send by every seconds. (0 to disable)")
                        bot_line_notify_trigger_by_temperature = gr.Slider(0, 100, value=60,
                                                                           label="2.3 Temperature Count",
                                                                           step=1,
                                                                           info="60°C/140°F")

                    bot_line_notify_send_with = gr.CheckboxGroup(["Image", "Text", "ScreenShot"],
                                                                 label="3. IF XXX Then [[[ YYY ]]]",
                                                                 info="then YYY(send text, image or both)?")
                    bot_line_notify_msg_header = gr.Textbox(label="4. [msg header]", lines=1,
                                                            value="[send from web-ui]",
                                                            placeholder="[send from web-ui]"
                                                            )
                    bot_line_notify_history = gr.Dataframe(
                        interactive=True,
                        wrap=True,
                        label="5. History",
                        headers=["TimeStamp", "Response", "Msg"],
                        datatype=["str", "str", "str"],
                        row_count=3,
                        col_count=(3, "fixed"),
                    )
                    bot_line_notify_send_button = gr.Button("Test Send(uncheck Timer checkbox click again to disable timer.)")

                with gr.Tab("Telegram-bot"):
                    gr.Markdown("* Generate forever mode \n"
                                "* Story board mode")
                    bot_telegram_enabled = gr.Checkbox(label=" bot_telegram_enabled", value=False)
                    bot_telegram_token_botid = gr.Textbox(label="1. [bot_line_notify_token_botid]", lines=1,
                                                          value="",
                                                          placeholder="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                                                          )
                    bot_telegram_token_chatid = gr.Textbox(label="1. [bot_line_notify_token_chatid]", lines=1,
                                                           value="",
                                                           placeholder="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                                                           )
                    bot_telegram_send_button = gr.Button("Test Send")

        bot_line_notify_trigger_by_temperature.change(fn=self.update_temperature_label,
                                                      inputs=bot_line_notify_trigger_by_temperature
                                                      )
        bot_line_notify_send_button.click(self.send_msg_linenotify,
                                          inputs=[bot_line_notify_token, bot_line_notify_trigger_by,
                                                  bot_line_notify_trigger_by_time_count,
                                                  bot_line_notify_send_with, bot_line_notify_msg_header],
                                          outputs=[bot_line_notify_history])
        return [bot_line_notify_enabled, bot_line_notify_enabled, bot_line_notify_token,
                bot_line_notify_trigger_by_time_count, bot_line_notify_msg_header,
                bot_telegram_enabled, bot_telegram_token_botid, bot_telegram_token_chatid]

    def after_component(self, component, **kwargs):
        if kwargs.get("elem_id") == "txt2img_prompt":
            self.boxx = component
        if kwargs.get("elem_id") == "img2img_prompt":
            self.boxxIMG = component

    def process(self, p: StableDiffusionProcessingTxt2Img,
                bot_line_notify_enabled, bot_line_notify_token, bot_line_notify_trigger_by,
                bot_line_notify_trigger_by_time_count,
                bot_line_notify_send_with, bot_line_notify_msg_header,
                bot_telegram_enabled, bot_telegram_token_botid, bot_telegram_token_chatid):

        if bot_line_notify_enabled:
            log.warning(f"[][][bot_line_notify_enabled]: {bot_line_notify_token}")
            self.send_msg_linenotify(bot_line_notify_token, bot_line_notify_trigger_by,
                                     bot_line_notify_trigger_by_time_count,
                                     bot_line_notify_send_with, bot_line_notify_msg_header)

        if bot_telegram_enabled:
            log.warning(f"[][][call_llm_translate]: {bot_telegram_enabled}")
