FROM indigodatacloudapps/powerfit

RUN sudo apt update -y && \
	sudo apt install python3-pandas -y && \
	sudo apt-get install python3-openpyxl -y

COPY . /home

WORKDIR /home

RUN rm -r GroEL-GroES && \
	rm run-powerfitCPU.sh && \
	rm run-powerfitGPU.sh








