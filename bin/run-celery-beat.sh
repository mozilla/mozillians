#!/bin/bash

celery -A mozillians beat -l INFO
