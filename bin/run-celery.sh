#!/bin/bash

celery -A mozillians worker -l INFO
