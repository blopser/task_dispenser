set -e

! mkdir $VIRTUAL_ENV -p

if [ ! -w "$VIRTUAL_ENV" ]; then
  echo ERROR: \"$VIRTUAL_ENV\" path is not writable
  ls -lah $VIRTUAL_ENV
  exit 1
fi


if [ -z "$( ls -A $VIRTUAL_ENV )" ]; then
  echo "Init virtual env"
  /usr/local/bin/python -m venv $VIRTUAL_ENV
  touch $VIRTUAL_ENV/requirements.txt
fi


if [[ ! -f /etc/requirements.txt ]]; then
  if [[ $PIP_REQUIREMENTS ]]; then
    echo ${PIP_REQUIREMENTS} | tr ' ' '\n' > /tmp/requirements.txt
  fi
else
  cp /etc/requirements.txt /tmp/requirements.txt
fi

if [[ -f /tmp/requirements.txt ]]; then
  REQUIREMENTS_CHANGED="$(cmp $VIRTUAL_ENV/requirements.txt /tmp/requirements.txt -s; echo $?)"

  if [[ $REQUIREMENTS_CHANGED -ne 0 ]]; then
    echo 'Install pip requirements'
    python -m pip install -U pip
    python -m pip install -r /tmp/requirements.txt
    cp /tmp/requirements.txt $VIRTUAL_ENV/requirements.txt
  fi
fi

exec "$@"
