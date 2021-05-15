#!/usr/bin/env bash

# If not specify, default meaning of return value:
# 0: Success
# 1: System error
# 2: Network error

MIKAN_SPIDER_HOME="/srv/mikanSpider/"
MIKAN_SPIDER_REPO="https://github.com/dagger11263/mikanSpider.git"

######### color code ########
RED="31m"
GREEN="32m"
BLUE="36m"
#############################

colorEcho() {
  COLOR=$1
  echo -e "\033[${COLOR}${*:2}\033[0m"
}

downloadMikanSpider() {
  if [[ -d ${MIKAN_SPIDER_HOME} ]]; then
    rm -r ${MIKAN_SPIDER_HOME}
  fi
  colorEcho ${BLUE} "Downloading mikanSpider: ${MIKAN_SPIDER_REPO}."
  if ! git clone -b master ${MIKAN_SPIDER_REPO}; then
    colorEcho ${RED} "Failed to download mikanSpider! Please check your network."
    return 2
  fi
  return 0
}

createPythonVenv() {
  colorEcho ${BLUE} "Creating python venv for mikanSpider."
  PYTHON_COMMAND=$(command -v python3.8 || command -v python3.7)
  if [[ -z $PYTHON_COMMAND ]]; then
    colorEcho ${RED} "Failed to create python venv, python version >= 3.7 required."
    return 1
  fi

  if [[ -n $(command -v apt) ]]; then
    # Use virtualenv on Ubuntu Server 18.04 LTS.
    if [[ -z $(command -v virtualenv) ]]; then
      # Install virtualenv.
      if ! $PYTHON_COMMAND -m pip install virtualenv; then
        colorEcho ${RED} "Failed to install virtualenv! Please check your network."
        return 2
      fi
    fi
    virtualenv --no-wheel --python="$PYTHON_COMMAND" ${MIKAN_SPIDER_HOME}venv
  else
    # Use python venv on Manjaro Linux.
    $PYTHON_COMMAND -m venv ${MIKAN_SPIDER_HOME}venv
  fi
  return 0
}

initPythonVenv() {
  colorEcho ${BLUE} "Initialize venv, this will install python packages from requirements.txt."
  # shellcheck source=/srv/mikanSpider/venv/bin/activate
  source ${MIKAN_SPIDER_HOME}venv/bin/activate
  if ! pip install -r ${MIKAN_SPIDER_HOME}requirements.txt; then
    colorEcho ${RED} "Failed to install packages from requirements.txt! Please check your network."
    return 2
  fi
  return 0
}

addCronJob() {
  colorEcho ${BLUE} "Creating a cron job for mikanSpider."
  if ! {
    crontab -l 2> /dev/null
    echo "0 3 * * * cd ${MIKAN_SPIDER_HOME} && venv/bin/python main.py"
  } | uniq | crontab -u "$(logname)" -; then
    colorEcho ${RED} "Failed to create a cron job for mikanSpider."
    return 1
  fi
  return 0
}

main() {
  if [[ $(id -u) -ne 0 ]]; then
    colorEcho ${RED} "You must run this script with root permission."
    return 1
  fi
  cd /srv || return 1
  umask 0022
  downloadMikanSpider || return $?
  createPythonVenv || return $?
  initPythonVenv || return $?
  addCronJob || return $?
  chown -R "$(logname)": "${MIKAN_SPIDER_HOME}"
  colorEcho ${GREEN} "All tasks are done."
  return 0
}

main
