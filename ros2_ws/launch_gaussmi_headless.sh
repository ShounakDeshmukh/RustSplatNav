#!/bin/bash
# Headless GauSS-MI launcher - disables GUI to avoid import errors

docker exec -it gaussmi_ros1 bash -lc '
source /opt/ros/noetic/setup.bash && \
source /opt/conda/etc/profile.d/conda.sh && \
conda activate GauSS-MI && \
unset PYTHONPATH && \
export PYTHONPATH=/opt/ros/noetic/lib/python3/dist-packages && \
cd /home/do/ws_gaussmi/src/GauSS-MI && \
python -c "import pathlib,yaml; src=pathlib.Path(\"configs/online_gs_map.yaml\"); dst=pathlib.Path(\"/tmp/online_gs_map_nogui.yaml\"); cfg=yaml.safe_load(src.read_text()); cfg.setdefault(\"Results\", {})[\"use_gui\"]=False; dst.write_text(yaml.safe_dump(cfg, sort_keys=False)); print(f\"Wrote {dst} with Results.use_gui=False\")" && \
cd /home/do/ws_gaussmi && \
source devel/setup.bash && \
roslaunch gs_mapping gaussmi_active.launch gs_config_path:=/tmp/online_gs_map_nogui.yaml
'
