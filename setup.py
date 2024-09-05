# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from setuptools import setup, find_packages

print("install package ...\n", find_packages())

with open('requirements.txt') as f:
    requirements = f.readlines()


setup(
    name="gradio_tunnel_frpc",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        '': ['*'],  # 包含所有二进制文件
    },
    install_requires=requirements,
)
