# gradio-tunnel-frpc
基于内网应用的穿透服务，可以批量注册网站，进行穿透代理

## 安装
```bash
pip install git+https://github.com/aigc-open/gradio-tunnel-frpc.git
```

## 使用
```bash
python3 -m gradio_tunnel_frpc.web main -p 7861
python3 -m gradio_tunnel_frpc.web single 127.0.0.1:80
```


## 效果
![](demo.png)
