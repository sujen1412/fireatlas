FROM mas.maap-project.org/root/maap-workspaces/base_images/vanilla:v3.1.4
ARG BUILD_MAPP_PGT_ARG
ENV MAAP_PGT=$BUILD_MAPP_PGT_ARG
RUN pip install git+https://github.com/MAAP-Project/maap-py.git@develop
COPY ./maap_runtime/submit-dps-job.py submit-dps-job.py
ENTRYPOINT ["bash", "-c", "export MAAP_PGT=${MAAP_PGT} && . /opt/conda/etc/profile.d/conda.sh && conda activate vanilla &&  python submit-dps-job.py \"$@\"", "bash"]
