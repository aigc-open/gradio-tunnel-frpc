import gradio as gr
from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage
from gradio_tunnel_frpc.tunnel import setup_tunnel
import secrets
import threading
import os
import time
import os
db = None
expire_time = 3600 * 24 * 3

def _tables(data:list=[]):
    """
    data: 穿透服务列表
    以markdown格式返回表格,表头为穿透地址和共享地址
    :return:
    """
    header = "| 穿透地址 | 共享地址 | 过期时间 |\n"
    header += "| --- | --- | --- |\n"
    tables = header
    
    
    for item in data:
        if item.get("expire_timestamp"):
            time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item['expire_timestamp']))
        else:
            time_str = "稍等..."
        tables += f"| {item['remote_url']} | {item['share_address']} | {time_str} |\n"
    return tables


def _generate(remote_url=""):
    remote_url = remote_url.strip()
    ip, port = remote_url.split(":")
    share_token = secrets.token_urlsafe(32)
    while True:
        if not db.search(Query().remote_url.matches(remote_url)):
            os.system(f"ps -ef | grep {share_token} "+ "| awk '{print $2}' | xargs kill -9")
            break
        share_token = secrets.token_urlsafe(32)
        os.system(f"ps -ef | grep {share_token} "+ "| awk '{print $2}' | xargs kill -9")
        share_address = setup_tunnel(local_host=ip, local_port=port, share_token=share_token, share_server_address=None).start_tunnel()
        expire_timestamp = time.time() + expire_time
        db.update({"share_address": share_address, "expire_timestamp": expire_timestamp}, Query().remote_url.matches(remote_url))
        while True:
            if not db.search(Query().remote_url.matches(remote_url)):
                os.system(f"ps -ef | grep {share_token} "+ "| awk '{print $2}' | xargs kill -9")
                break
            if time.time() > expire_timestamp:
                os.system(f"ps -ef | grep {share_token} "+ "| awk '{print $2}' | xargs kill -9")
                break

    
def _register(remote_url):
    remote_url = remote_url.strip()
    if not remote_url:
        gr.Warning("请输入穿透服务器地址")
        return _tables(db.all())
    if db.search(Query().remote_url.matches(remote_url)):
        gr.Warning("该穿透地址已存在")
        return _tables(db.all())
    db.insert({"remote_url": remote_url, "share_address": "", "expire_timestamp": ""})
    threading.Thread(target=_generate, args=[remote_url]).start() # 开启线程处理
    time.sleep(2)
    gr.Info("注册成功, 请点击查询")
    return _tables(db.all())


def _search(remote_url=""):
    remote_url = remote_url.strip()
    query = Query()
    if query:
        data = db.search(query.remote_url.matches(remote_url))
    else:
        data = db.all()
    return _tables(data)


def _delete(remote_url=""):
    remote_url = remote_url.strip()
    if not remote_url:
        gr.Warning("请输入穿透服务器地址")
        return _tables(db.all())
    query = Query()
    if query:
        db.remove(query.remote_url.matches(remote_url))
    else:
        db.purge()
    gr.Info("删除成功")
    return _tables(db.all())

def main(port=7860):
    global db
    db = TinyDB(storage=MemoryStorage)
    CSS = """
    .duplicate-button {
    margin: auto !important;
    color: white !important;
    background: black !important;
    border-radius: 100vh !important;
    }
    """
    with gr.Blocks(css=CSS, theme="soft", fill_height=True) as demo:
        gr.Markdown("## 免费内网穿透工具")
        with gr.Row():
            remote_url = gr.Textbox(label="请输入穿透服务器地址", info="格式: 127.0.0.1:7890")
            with gr.Column():
                register_btn = gr.Button("注册")
                search_btn = gr.Button("查询")
                del_btn = gr.Button("移除穿透服务")
        tables = gr.Markdown("")

        register_btn.click(fn=_register, inputs=[remote_url],outputs=[tables])
        search_btn.click(fn=_search, inputs=[remote_url],outputs=[tables])
        del_btn.click(fn=_delete, inputs=[remote_url],outputs=[tables])

    demo.launch(server_name="0.0.0.0", server_port=port)

def single(remote_url):
    global db
    db = TinyDB('frpc.json')
    _delete(remote_url)
    _register(remote_url)
    while True:
        pass

if __name__ == "__main__":
    from fire import Fire
    Fire()
        
