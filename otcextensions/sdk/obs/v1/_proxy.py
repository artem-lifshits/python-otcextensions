# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# import os

from openstack import _log
from openstack import proxy

from otcextensions.sdk.obs.v1 import container as _container
from otcextensions.sdk.obs.v1 import obj as _obj

_logger = _log.setup_logging('openstack')

# TODO(agoncharov) regulate use of exceptions


def _normalize_obs_keys(obj):
    return {k.lower(): v for k, v in obj.items()}


class Proxy(proxy.BaseProxy):

    SESSION_ATTR_NAME = '_boto_session'

    def _set_ak(self, ak, sk):
        """Inject AK/SK into the proxy for use

        """
        _logger.debug('injecting ak/sk')
        setattr(self, 'AK', ak)
        setattr(self, 'SK', sk)

        pass

    def get_endpoint(self, **kwargs):
        """Override to return mapped endpoint if override and region are set

        """
        region = getattr(self, 'region_name', 'eu-de')
        if not region:
            # region_name attr might be set to empty
            region = 'eu-de'
        override = getattr(self, 'endpoint_override',
                           'https://obs.%(region_name)s.otc.t-systems.com')
        if region and override:
            return override % {'region_name': region}
        else:
            return super(Proxy, self).get_endpoint(**kwargs)

    # ======== Containers ========

    def containers(self, **query):
        """Obtain Container objects for this account.

        :param kwargs query: Optional query parameters to be sent to limit
                                 the resources being returned.

        :rtype: A generator of
            :class:`~openstack.object_store.v1.container.Container` objects.
        """
        return self._list(_container.Container, paginated=True, **query)

    def get_container(self, container):
        """Get the detail of a container

        :param id: Container id or an object of class
                   :class:`~otcextensions.sdk.obs.v1.container.Container`
        :returns: Detail of container
        :rtype: :class:`~otcextensions.sdk.obs.v1.container.Container`
        """
        return self._get(_container.Container, container)

    def create_container(self, name, **attrs):
        """Create a new container from attributes

        :param container: Name of the container to create.
        :param dict attrs: Keyword arguments which will be used to create
               a :class:`~openstack.object_store.v1.container.Container`,
               comprised of the properties on the Container class.

        :returns: The results of container creation
        :rtype: :class:`~openstack.object_store.v1.container.Container`
        """
        return self._create(_container.Container, name=name, **attrs)

    def delete_container(self, container, ignore_missing=True):
        """Delete a container

        :param container: The value can be either the name of a container or a
                      :class:`~openstack.object_store.v1.container.Container`
                      instance.
        :param bool ignore_missing: When set to ``False``
                    :class:`~openstack.exceptions.ResourceNotFound` will be
                    raised when the container does not exist.
                    When set to ``True``, no exception will be set when
                    attempting to delete a nonexistent server.

        :returns: ``None``
        """
        self._delete(_container.Container, container,
                     ignore_missing=ignore_missing)

    def get_container_metadata(self, container):
        """Get metadata for a container

        :param container: The value can be the name of a container or a
               :class:`~openstack.object_store.v1.container.Container`
               instance.

        :returns: One :class:`~openstack.object_store.v1.container.Container`
        :raises: :class:`~openstack.exceptions.ResourceNotFound`
                 when no resource can be found.
        """
        raise NotImplementedError
        return self._head(_container.Container, container)

    def set_container_metadata(self, container, **metadata):
        """Set metadata for a container.

        :param container: The value can be the name of a container or a
               :class:`~openstack.object_store.v1.container.Container`
               instance.
        :param kwargs metadata: Key/value pairs to be set as metadata
                                on the container. Both custom and system
                                metadata can be set. Custom metadata are keys
                                and values defined by the user. System
                                metadata are keys defined by the Object Store
                                and values defined by the user. The system
                                metadata keys are:

                                - `content_type`
                                - `is_content_type_detected`
                                - `versions_location`
                                - `read_ACL`
                                - `write_ACL`
                                - `sync_to`
                                - `sync_key`
        """
        raise NotImplementedError
        res = self._get_resource(_container.Container, container)
        res.set_metadata(self, metadata)
        return res

    def delete_container_metadata(self, container, keys):
        """Delete metadata for a container.

        :param container: The value can be the ID of a container or a
               :class:`~openstack.object_store.v1.container.Container`
               instance.
        :param keys: The keys of metadata to be deleted.
        """
        raise NotImplementedError
        res = self._get_resource(_container.Container, container)
        res.delete_metadata(self, keys)
        return res

    # ======== Objects ========

    def objects(self, container, **query):
        """Return a generator that yields the Container's objects.

        :param container: A container object or the name of a container
            that you want to retrieve objects from.
        :type container:
            :class:`~openstack.object_store.v1.container.Container`
        :param kwargs \*\*query: Optional query parameters to be sent to limit
                                 the resources being returned.

        :rtype: A generator of
            :class:`~openstack.object_store.v1.obj.Object` objects.
        """
        container = self._get_container_name(container=container)

        for obj in self._list(
                _obj.Object, container=container,
                paginated=True, **query):
            obj.container = container
            yield obj

    def _get_container_name(self, obj=None, container=None):
        if obj is not None:
            obj = self._get_resource(_obj.Object, obj)
            if obj.container is not None:
                return obj.container
        if container is not None:
            container = self._get_resource(_container.Container, container)
            return container.name

        raise ValueError("container must be specified")

    def get_object(self, obj, container=None):
        """Get the data associated with an object

        :param obj: The value can be the name of an object or a
                       :class:`~openstack.object_store.v1.obj.Object` instance.
        :param container: The value can be the name of a container or a
               :class:`~openstack.object_store.v1.container.Container`
               instance.

        :returns: The contents of the object.  Use the
                  :func:`~get_object_metadata`
                  method if you want an object resource.
        :raises: :class:`~openstack.exceptions.ResourceNotFound`
                 when no resource can be found.
        """
        container_name = self._get_container_name(
            obj=obj, container=container)
        return self._get(_obj.Object, obj, container=container_name)

    def download_object(self, obj, container=None, **attrs):
        """Download the data contained inside an object.

        :param obj: The value can be the name of an object or a
                       :class:`~openstack.object_store.v1.obj.Object` instance.
        :param container: The value can be the name of a container or a
               :class:`~openstack.object_store.v1.container.Container`
               instance.

        :raises: :class:`~openstack.exceptions.ResourceNotFound`
                 when no resource can be found.
        """
        container_name = self._get_container_name(
            obj=obj, container=container)
        obj = self._get_resource(
            _obj.Object, obj, container=container_name, **attrs)
        return obj.download(self, filename=attrs.pop('file', '-'))

    def stream_object(self, obj, container=None, chunk_size=1024, **attrs):
        """Stream the data contained inside an object.

        :param obj: The value can be the name of an object or a
                       :class:`~openstack.object_store.v1.obj.Object` instance.
        :param container: The value can be the name of a container or a
               :class:`~openstack.object_store.v1.container.Container`
               instance.

        :raises: :class:`~openstack.exceptions.ResourceNotFound`
                 when no resource can be found.
        :returns: An iterator that iterates over chunk_size bytes
        """
        container_name = self._get_container_name(
            obj=obj, container=container)
        container_name = self._get_container_name(container=container)
        obj = self._get_resource(
            _obj.Object, obj, container=container_name, **attrs)
        return obj.stream(self, chunk_size=chunk_size)

    def create_object(self, container, name, **attrs):
        """Upload a new object from attributes

        :param container: The value can be the name of a container or a
               :class:`~openstack.object_store.v1.container.Container`
               instance.
        :param name: Name of the object to create.
        :param dict attrs: Keyword arguments which will be used to create
               a :class:`~openstack.object_store.v1.obj.Object`,
               comprised of the properties on the Object class.

        :returns: The results of object creation
        :rtype: :class:`~openstack.object_store.v1.container.Container`
        """
        # TODO(mordred) Add ability to stream data from a file
        # TODO(mordred) Use create_object from OpenStackCloud
        container_name = self._get_container_name(container=container)
        return self._create(
            _obj.Object, container=container_name, name=name, **attrs)
    # Backwards compat
    upload_object = create_object

    def copy_object(self):
        """Copy an object."""
        raise NotImplementedError

    def delete_object(self, obj, ignore_missing=True, container=None):
        """Delete an object

        :param obj: The value can be either the name of an object or a
                       :class:`~openstack.object_store.v1.container.Container`
                       instance.
        :param container: The value can be the ID of a container or a
               :class:`~openstack.object_store.v1.container.Container`
               instance.
        :param bool ignore_missing: When set to ``False``
                    :class:`~openstack.exceptions.ResourceNotFound` will be
                    raised when the object does not exist.
                    When set to ``True``, no exception will be set when
                    attempting to delete a nonexistent server.

        :returns: ``None``
        """
        container_name = self._get_container_name(obj, container)

        self._delete(_obj.Object, obj, ignore_missing=ignore_missing,
                     container=container_name)

    def get_object_metadata(self, obj, container=None):
        """Get metadata for an object.

        :param obj: The value can be the name of an object or a
                    :class:`~openstack.object_store.v1.obj.Object` instance.
        :param container: The value can be the ID of a container or a
               :class:`~openstack.object_store.v1.container.Container`
               instance.

        :returns: One :class:`~openstack.object_store.v1.obj.Object`
        :raises: :class:`~openstack.exceptions.ResourceNotFound`
                 when no resource can be found.
        """
        raise NotImplementedError
        container_name = self._get_container_name(obj, container)

        return self._head(_obj.Object, obj, container=container_name)

    def set_object_metadata(self, obj, container=None, **metadata):
        """Set metadata for an object.

        Note: This method will do an extra HEAD call.

        :param obj: The value can be the name of an object or a
                    :class:`~openstack.object_store.v1.obj.Object` instance.
        :param container: The value can be the name of a container or a
               :class:`~openstack.object_store.v1.container.Container`
               instance.
        :param kwargs metadata: Key/value pairs to be set as metadata
                                on the container. Both custom and system
                                metadata can be set. Custom metadata are keys
                                and values defined by the user. System
                                metadata are keys defined by the Object Store
                                and values defined by the user. The system
                                metadata keys are:

                                - `content_type`
                                - `content_encoding`
                                - `content_disposition`
                                - `delete_after`
                                - `delete_at`
                                - `is_content_type_detected`
        """
        raise NotImplementedError
        container_name = self._get_container_name(obj, container)
        res = self._get_resource(_obj.Object, obj, container=container_name)
        res.set_metadata(self, metadata)
        return res

    def delete_object_metadata(self, obj, container=None, keys=None):
        """Delete metadata for an object.

        :param obj: The value can be the name of an object or a
                    :class:`~openstack.object_store.v1.obj.Object` instance.
        :param container: The value can be the ID of a container or a
               :class:`~openstack.object_store.v1.container.Container`
               instance.
        :param keys: The keys of metadata to be deleted.
        """
        raise NotImplementedError
        container_name = self._get_container_name(obj, container)
        res = self._get_resource(_obj.Object, obj, container=container_name)
        res.delete_metadata(self, keys)
        return res
