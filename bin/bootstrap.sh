#!/usr/bin/env bash

DGRPC_DIR=/users/glawler/src/distributed_agents
INSTALL_LOG=/tmp/dgprc-install.log

if [[ $(id -u) -ne 0 ]]; then 
    echo This script must be run as root.
    exit 1
fi

# install python package
pushd ${DGRPC_DIR} &> ${INSTALL_LOG}
python3 ./setup.py install &> ${INSTALL_LOG}
popd ${DGRPC_DIR} &> ${INSTALL_LOG}

# now setup to run as a service/daemon
if [[ ! -e /usr/bin/lsb_release ]]; then 
    echo Unsupported platform for service. Install by hand.
    exit 1
fi

LSB_ID=$(/usr/bin/lsb_release -i | awk '{print $3}')
LSB_REL=$(/usr/bin/lsb_release -r | awk '{print $2}')
case ${LSB_ID} in 
    Ubuntu) echo Installing service on Ubuntu;
        case ${LSB_REL} in
            14.*)
                echo Installing services as an upstart service.
                if [[ -e /etc/init.d/dgprc ]]; then 
                    update-rc.d -f dgrpc remove
                fi
                cp ${DGRPC_DIR}/etc/dgrpc.upstart /etc/init.d/dgrpc;
                chmod 755 /etc/init.d/dgrpc
                update-rc.d dgrpc defaults 99
                /etc/init.d/dgrpc start
                /etc/init.d/dgrpc status
                ;;
            16.*)
                echo Installing service as a systemd service. 
                cp ${DGRPC_DIR}/etc/dgrpc.service /lib/systemd/system ;
                service dgrpc start ;
                ;;
            *)
                echo Unsupported version of ${LSB_ID}, ${LSB_REL}. Please install service by hand.
                exit 1
        esac
        ;;
    *)
        echo Unsupported OS ${LSB_ID} ${LSB_REL}. Please install service by hand.
        exit 1
        ;;
esac

