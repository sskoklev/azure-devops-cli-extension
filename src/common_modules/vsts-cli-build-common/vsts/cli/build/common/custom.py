# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import logging

from vsts.build.v4_0.models.build import Build
from vsts.build.v4_0.models.definition_reference import DefinitionReference
from vsts.cli.common.exception_handling import handle_command_exception
from vsts.cli.common.git import resolve_git_ref_heads
from vsts.cli.common.services import (get_build_client,
                                      get_git_client,
                                      resolve_instance_and_project,
                                      resolve_instance_project_and_repo)
from vsts.cli.common.uri import uri_quote
from vsts.cli.common.uuid import is_uuid
from webbrowser import open_new


def build_queue(definition_id=None, name=None, source_branch=None, open_browser=False, team_instance=None, project=None, detect=None):
    """Queue a new build.
    :param definition_id: The id of the build definition.  Required if --name is not supplied.
    :type definition_id: str
    :param name: The name of the build definition.  Ignored if --id is supplied.
    :type name: str
    :param source_branch: The source branch to build.
    :type source_branch: str
    :param open_browser: Open the work item in the default web browser.
    :type open_browser: bool
    :param team_instance: The URI for the VSTS account (https://<account>.visualstudio.com) or your TFS project
                          collection.
    :type team_instance: str
    :param project: Name or ID of the team project.
    :type project: str
    :param detect: When 'On' unsupplied arg values will be detected from the current working
                   directory's repo.
    :type detect: str
    :rtype: :class:`<Build> <build.v4_0.models.Build>`
    """
    try:
        team_instance, project = resolve_instance_and_project(detect=detect,
                                                              team_instance=team_instance,
                                                              project=project)
        if definition_id is None and name is None:
            raise ValueError("Either the --id argument or the --name argument must be supplied for this command.")
        client = get_build_client(team_instance)
        if definition_id is None:
            definition_id = get_definition_id_from_name(name, client, project)
        definition_reference = DefinitionReference(id=definition_id)
        build = Build(definition=definition_reference)
        if source_branch is not None:
            build.source_branch = resolve_git_ref_heads(source_branch)
        queued_build = client.queue_build(build=build, project=project)
        if open_browser:
            _open_build(queued_build, team_instance)
        return queued_build
    except Exception as ex:
        handle_command_exception(ex)


def build_show(build_id, open_browser=False, team_instance=None, project=None, detect=None):
    """Show a build.
    :param build_id: The id of the build.
    :type build_id: int
    :param open_browser: Open the work item in the default web browser.
    :type open_browser: bool
    :param team_instance: The URI for the VSTS account (https://<account>.visualstudio.com) or your TFS project
                          collection.
    :type team_instance: str
    :param project: Name or ID of the team project.
    :type project: str
    :param detect: When 'On' unsupplied arg values will be detected from the current working
                   directory's repo.
    :type detect: str
    :rtype: :class:`<Build> <build.v4_0.models.Build>`
    """
    try:
        team_instance, project = resolve_instance_and_project(detect=detect,
                                                              team_instance=team_instance,
                                                              project=project)
        client = get_build_client(team_instance)
        build = client.get_build(build_id=build_id, project=project)
        if open_browser:
            _open_build(build, team_instance)
        return build
    except Exception as ex:
        handle_command_exception(ex)


def build_definition_list(name=None, top=None, team_instance=None, project=None, repository=None, detect=None):
    """Lists build definitions
    :param name: Filters to definitions whose names equal this value. Append a * to filter to definitions whose names
                 start with this value. For example: MS*
    :type name: bool
    :param top: The maximum number of definitions to return.
    :type top: int
    :param team_instance: The URI for the VSTS account (https://<account>.visualstudio.com) or your TFS project
                          collection.
    :type team_instance: str
    :param project: Name or ID of the team project.
    :type project: str
    :param repository: Name or ID of the repository.
    :type repository: str
    :param detect: When 'On' unsupplied arg values will be detected from the current working
                   directory's repo.
    :type detect: str
    :rtype: [BuildDefinitionReference]
    """
    try:
        team_instance, project, repo = resolve_instance_project_and_repo(detect=detect,
                                                                         team_instance=team_instance,
                                                                         project=project,
                                                                         repo=repository)
        client = get_build_client(team_instance)
        query_order = 'DefinitionNameAscending'
        repository_type = None
        if repository is not None:
            resolved_repository = _resolve_repository_as_id(repository, team_instance, project)
            if resolved_repository is None:
                raise ValueError("Could not find a repository with name, '{}', in project, '{}'.".format(repository,
                                                                                                         project))
            else:
                repository_type = 'TfsGit'
        else:
            resolved_repository = None
        definition_references = client.get_definitions(project=project, name=name, repository_id=resolved_repository,
                                                       repository_type=repository_type, top=top,
                                                       query_order=query_order)
        return definition_references
    except Exception as ex:
        handle_command_exception(ex)


def build_definition_show(definition_id=None, name=None, open_browser=False, team_instance=None, project=None,
                          detect=None):
    """Shows details of a build definition.
    :param definition_id: The ID of the Build Definition.
    :type definition_id: int
    :param name: The name of the Build Definition.  Ignored if id is supplied.
    :type name: str
    :param open_browser: Open the work item in the default web browser.
    :type open_browser: bool
    :param team_instance: The URI for the VSTS account (https://<account>.visualstudio.com) or your TFS project
                          collection.
    :type team_instance: str
    :param project: Name or ID of the team project.
    :type project: str
    :param detect: When 'On' unsupplied arg values will be detected from the current working
                   directory's repo.
    :type detect: str
    :rtype: BuildDefinitionReference
    """
    try:
        team_instance, project = resolve_instance_and_project(detect=detect,
                                                              team_instance=team_instance,
                                                              project=project)
        client = get_build_client(team_instance)
        if definition_id is None:
            if name is not None:
                definition_id = get_definition_id_from_name(name, client, project)
            else:
                raise ValueError("Either the --id argument or the --name argument must be supplied for this command.")
        build_definition = client.get_definition(definition_id=definition_id, project=project)
        if open_browser:
            _open_definition(build_definition, team_instance)
        return build_definition
    except Exception as ex:
        handle_command_exception(ex)


def _open_build(build, team_instance):
    """Opens the build in the default browser.
    :param :class:`<Build> <build.v4_0.models.Build>` build:
    :param str team_instance:
    """
    # https://mseng.visualstudio.com/vsts-cli/_build/index?buildId=4053990
    project = build.project.name
    url = team_instance.rstrip('/') + '/' + uri_quote(project) + '/_build/index?buildid='\
        + uri_quote(str(build.id))
    logging.debug('Opening web page: %s', url)
    open_new(url=url)


def _open_definition(definition, team_instance):
    """Opens the build definition in the default browser.
    :param :class:`<BuildDefinitionReference> <build.v4_0.models.BuildDefinitionReference>` definition:
    :param str team_instance:
    """
    # https://mseng.visualstudio.com/vsts-cli/_build/index?definitionId=5419
    project = definition.project.name
    url = team_instance.rstrip('/') + '/' + uri_quote(project) + '/_build/index?definitionId='\
        + uri_quote(str(definition.id))
    logging.debug('Opening web page: %s', url)
    open_new(url=url)


def get_definition_id_from_name(name, client, project):
    definition_references = client.get_definitions(project=project, name=name)
    if len(definition_references) == 1:
        return definition_references[0].id
    elif len(definition_references) > 1:
        if is_uuid(project):
            project = definition_references[0].project.name
        message = 'Multiple definitions were found matching name "{name}" in project "{project}".  Try '\
                  + 'supplying the definition ID.'
        raise ValueError(message.format(name=name, project=project))
    else:
        raise ValueError('There were no build definitions matching name "{name}" in project "{project}".'
                         .format(name=name, project=project))


def _resolve_repository_as_id(repository, team_instance, project):
    if is_uuid(repository):
        return repository
    else:
        git_client = get_git_client(team_instance)
        repositories = git_client.get_repositories(project=project, include_links=False, include_all_urls=False)
        for found_repository in repositories:
            if found_repository.name.lower() == repository.lower():
                return found_repository.id
