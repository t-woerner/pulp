Installation Instructions
=========================

Ansible
-------

PyPI
----

.. tip::

    These are the manual steps to install Pulp. There are Ansible roles that will do all
    of the following for you.

1. Install python3.5 and virtualenv::

   $ sudo dnf install python3
   $ sudo pip3 install virtualenv

2. Create a pulp virtualenv::

   $ virtualenv {virtualenv} -p python3
   $ source {virtualenv}/bin/activate

3. Install Pulp::

   $ pip3 install pulpcore

4. If the the server.yaml file isn't in the default location of `/etc/pulp/server.yaml`, set the
   PULP_SETTINGS environment variable to tell pulp where to find you server.yaml file.
   ``export PULP_SETTINGS={virtualenv}/lib/python3.5/site-packages/pulpcore/etc/pulp/server.yaml``

5. Add a ``SECRET_KEY`` to your :ref:`server.yaml <server-conf>` file

6. Tell Django which settings you're using::

   $ export DJANGO_SETTINGS_MODULE=pulpcore.app.settings

7. Go through the  :ref:`database-install`, :ref:`broker-install`, and `systemd-setup` sections

8. Run Django Migrations::

   $ django-admin migrate --noinput auth
   $ django-admin migrate --noinput
   $ django-admin reset-admin-password --password admin

9. Run Pulp::

   $ django-admin runserver

CentOS, RHEL, Fedora
--------------------

Source
------

.. _database-install:

Database
--------

.. tip::

    These are the manual steps to install the database. There are Ansible roles that will do all
    of the following for you.

You must provide a running Postgres instance for Pulp to use. You can use the same host that you
will run Pulp on, or you can give Postgres its own separate host if you like::

   $ sudo dnf install postgresql postgresql-server python3-psycopg2
   $ sudo postgresql-setup --initdb /var/lib/pgsql/data/base

After installing Postgres, you should configure it to start at boot and start it::

   $ sudo systemctl enable postgresql
   $ sudo systemctl start postgresql

Initialize the pulp database::

   $ sudo -u postgres -i bash
   $ createuser --username=postgres -d -l pulp
   $ createdb --owner=pulp --username=postgres pulp

Don't forget to update your `/var/lib/pgsql/data/pg_hba.conf
<https://www.postgresql.org/docs/9.1/static/auth-pg-hba-conf.html>`_ file, to grant an appropriate
level of database access.

Restart Postgres after updating ``pg_hba.conf``::

   $ sudo systemctl restart postgresql

.. _broker-install:

Message Broker
--------------

.. tip::

    These are the manual steps to install the broker. There are Ansible roles that will install all
    of the following for you.

You must also provide a message broker for Pulp to use. Pulp will work with Qpid or RabbitMQ.
This can be on a different host or the same host that Pulp is running on.


qpidd
^^^^^

To install qpidd, run this command on the host you wish to be the message broker::

   $ sudo dnf install qpid-cpp-server qpid-cpp-server-linearstore

After installing and configuring Qpid, you should configure it to start at boot and start it::

   $ sudo systemctl enable qpidd
   $ sudo systemctl start qpidd


RabbitMQ
^^^^^^^^

To install RabbitMQ, run this command on the host you wish to be the message broker::

   $ sudo dnf install rabbitmq-server

After installing and configuring RabbitMQ, you should configure it to start at boot and start it::

   $ sudo systemctl enable rabbitmq-server
   $ sudo systemctl start rabbitmq-server

.. _systemd-setup:

Systemd
-------

.. tip::

    These are the manual steps to create the systemd files. There are Ansible roles that will do
    the following for you.


To run the Pulp services, three systemd files needs to be created in /etc/systemd/system/

pulp_celerybeat::

    [Unit]
    Description=Pulp Celerybeat
    After=network-online.target
    Wants=network-online.target

    [Service]
    # Set Environment if server.yaml is not in the default /etc/pulp/ directory
    Environment=PULP_SETTINGS=/path/to/pulp/server.yaml
    User=pulp
    WorkingDirectory=/var/run/pulp_celerybeat/
    RuntimeDirectory=pulp_celerybeat
    ExecStart=/path/to/python/bin/celery beat --app=pulpcore.tasking.celery_app:celery --scheduler=pulpcore.tasking.services.scheduler.Scheduler

    [Install]
    WantedBy=multi-user.target

pulp_resource_manager::

    [Unit]
    Description=Pulp Resource Manager
    After=network-online.target
    Wants=network-online.target

    [Service]
    # Set Environment if server.yaml is not in the default /etc/pulp/ directory
    Environment=PULP_SETTINGS=/path/to/pulp/server.yaml
    User=pulp
    WorkingDirectory=/var/run/pulp_resource_manager/
    RuntimeDirectory=pulp_resource_manager
    ExecStart=/path/to/python/bin/celery worker -A pulpcore.tasking.celery_app:celery -n resource_manager@%%h\
              -Q resource_manager -c 1 --events --umask 18\
              --pidfile=/var/run/pulp_resource_manager/resource_manager.pid

    [Install]
    WantedBy=multi-user.target


pulp_worker@::

    [Unit]
    Description=Pulp Celery Worker
    After=network-online.target
    Wants=network-online.target

    [Service]
    # Set Environment if server.yaml is not in the default /etc/pulp/ directory
    Environment=PULP_SETTINGS=/path/to/pulp/server.yaml
    User=pulp
    WorkingDirectory=/var/run/pulp_worker_%i/
    RuntimeDirectory=pulp_worker_%i
    ExecStart=/path/to/python/bin/celery worker -A pulpcore.tasking.celery_app:celery\
              -n reserved_resource_worker_%i@%%h -c 1 --events --umask 18\
              --pidfile=/var/run/pulp_worker_%i/reserved_resource_worker_%i.pid

    [Install]
    WantedBy=multi-user.target

These services can then be started by running::

    sudo systemctl start pulp_celerybeat
    sudo systemctl start pulp_resource_manager
    sudo systemctl start pulp_worker@1
    sudo systemctl start pulp_worker@2
