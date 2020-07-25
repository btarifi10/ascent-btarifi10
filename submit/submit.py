import multiprocessing
import os
import shutil
import subprocess
import sys
import re
import json
import threading
import time
from multiprocessing import Process

from utils import NeuronRunMode

ALLOWED_SUBMISSION_CONTEXTS = ['cluster', 'local']
OS = 'UNIX-LIKE' if any([s in sys.platform for s in ['darwin', 'linux']]) else 'WINDOWS'


def load(config_path: str):
    """
    Loads in json data and returns to user, assuming it has already been validated.
    :param config_path: the string path to load up
    :return: json data (usually dict or list)
    """
    with open(config_path, "r") as handle:
        # print('load "{}" --> key "{}"'.format(config, key))
        return json.load(handle)


def make_submission_list():
    if (not os.path.exists(os.path.join('MOD_Files/x86_64')) and OS is 'UNIX-LIKE') or \
            (not os.path.exists(os.path.join('MOD_Files', 'nrnmech.dll')) and OS is 'WINDOWS'):
        print('compile')
        os.chdir(os.path.join('MOD_Files'))
        subprocess.run(['nrnivmodl'], shell=True)
        os.chdir('..')

    for run_number in sys.argv[1:]:
        # run number is numeric
        assert re.search('[0-9]+', run_number), 'Encountered non-number run number argument: {}'.format(run_number)

        # build configuration filename
        filename = os.path.join('runs', run_number + '.json')

        # configuration file exists
        assert os.path.exists(filename), 'Run configuration not found: {}'.format(run_number)

        # load in configuration data
        run: dict = {}
        with open(filename, 'r') as file:
            run = json.load(file)

        # configuration is not empty
        assert len(run.items()) > 0, 'Encountered empty run configuration: {}'.format(filename)

        # assign appropriate configuration data
        sample = run.get('sample', [])
        models = run.get('models', [])
        sims = run.get('sims', [])
        submission_context = run.get('submission_context', 'cluster')

        # submission context is valid
        assert submission_context in ALLOWED_SUBMISSION_CONTEXTS, 'Invalid submission context: {}'.format(
            submission_context)

        if submission_context == 'local':
            local_run_keys = ['start_path', 'output_log', 'error_log']
            local_args = dict.fromkeys(local_run_keys, [])
            local_args_list = []

        # loop models, sims
        for model in models:
            for sim in sims:
                sim_dir = os.path.join('n_sims')
                sim_name_base = '{}_{}_{}_'.format(sample, model, sim)

                for sim_name in [x for x in os.listdir(sim_dir) if sim_name_base in x]:
                    sim_path = os.path.join(sim_dir, sim_name)
                    fibers_path = os.path.abspath(os.path.join(sim_path, 'data', 'inputs'))
                    output_path = os.path.abspath(os.path.join(sim_path, 'data', 'outputs'))
                    out_dir = os.path.abspath(os.path.join(sim_path, 'logs', 'out'))
                    err_dir = os.path.abspath(os.path.join(sim_path, 'logs', 'err'))

                    # ensure log directories exist
                    for cur_dir in [out_dir, err_dir]:
                        if not os.path.exists(cur_dir):
                            os.makedirs(cur_dir)

                    # ensure blank.hoc exists
                    blank_path = os.path.join(sim_path, 'blank.hoc')
                    if not os.path.exists(blank_path):
                        open(blank_path, 'w').close()

                    # load JSON file with binary search amplitudes
                    n_sim = sim_name.split('_')[-1]
                    sim_config = load(os.path.join(sim_path, '{}.json'.format(n_sim)))

                    print('\n\n################ {} ################\n\n'.format(sim_name))

                    if sim_config['protocol']['mode'] == NeuronRunMode.ACTIVATION_THRESHOLD.name \
                            or sim_config['protocol']['mode'] == NeuronRunMode.BLOCK_THRESHOLD.name:
                        stimamp_top = sim_config['protocol']['bounds_search']['top']
                        stimamp_bottom = sim_config['protocol']['bounds_search']['bottom']
                    elif sim_config['protocol']['mode'] == NeuronRunMode.FINITE_AMPLITUDES:
                        stimamp_top, stimamp_bottom = 0, 0

                    for fiber_filename in [x for x in os.listdir(fibers_path)
                                           if re.match('inner[0-9]+_fiber[0-9]+\\.dat', x)]:
                        master_fiber_name = str(fiber_filename.split('.')[0])
                        inner_name, fiber_name = tuple(master_fiber_name.split('_'))
                        inner_ind = int(inner_name.split('inner')[-1])
                        fiber_ind = int(fiber_name.split('fiber')[-1])

                        thresh_path = os.path.join(output_path,
                                                   'thresh_inner{}_fiber{}.dat'.format(inner_ind, fiber_ind))
                        if os.path.exists(thresh_path):
                            print('Found {} -->\t\tskipping inner ({}) fiber ({})'.format(thresh_path, inner_ind,
                                                                                          fiber_ind))
                            continue

                        start_path = os.path.join(sim_path, '{}_{}_start{}'.format(inner_ind, fiber_ind,
                                                                                   '.sh' if OS is 'UNIX_LIKE'
                                                                                   else '.bat'))

                        with open(start_path, 'w+') as handle:
                            lines = []
                            if OS is 'UNIX-LIKE':
                                lines = [
                                    '#!/bin/bash\n',
                                    'cd {}\n'.format(sim_path),
                                    'chmod a+rwx special\n',
                                    './special -nobanner '
                                    '-c \"strdef sim_path\" '
                                    '-c \"sim_path=\\\"{}\\\"\" '
                                    '-c \"inner_ind={}\" '
                                    '-c \"fiber_ind={}\" '
                                    '-c \"stimamp_top={}\" '
                                    '-c \"stimamp_bottom={}\" '
                                    '-c \"load_file(\\\"launch.hoc\\\")\" blank.hoc\n'.format(sim_path,
                                                                                              inner_ind,
                                                                                              fiber_ind,
                                                                                              stimamp_top,
                                                                                              stimamp_bottom)
                                ]

                                # copy special files ahead of time to avoid 'text file busy error'
                                shutil.copy(os.path.join('MOD_Files', 'x86_64', 'special'), sim_path)

                            else:  # OS is 'WINDOWS'
                                sim_path_win = os.path.join(*sim_path.split(os.pathsep)).replace('\\', '\\\\')
                                lines = [
                                    'nrniv -nobanner '
                                    '-dll {}/MOD_Files/nrnmech.dll '
                                    '-c \"strdef sim_path\" '
                                    '-c \"sim_path=\\\"{}\"\" '
                                    '-c \"inner_ind={}\" '
                                    '-c \"fiber_ind={}\" '
                                    '-c \"stimamp_top={}\" '
                                    '-c \"stimamp_bottom={}\" '
                                    '-c \"load_file(\\\"launch.hoc\\\")\" blank.hoc\n'.format(os.getcwd(),
                                                                                              sim_path_win,
                                                                                              inner_ind,
                                                                                              fiber_ind,
                                                                                              stimamp_top,
                                                                                              stimamp_bottom)
                                ]

                            handle.writelines(lines)
                            handle.close()

                        # submit batch job for fiber
                        job_name = '{}_{}'.format(sim_name, master_fiber_name)
                        output_log = os.path.join(out_dir, '{}{}'.format(master_fiber_name, '.log'))
                        error_log = os.path.join(err_dir, '{}{}'.format(master_fiber_name, '.log'))

                        if submission_context == 'cluster':
                            command = ' '.join([
                                'sbatch',
                                '--job-name={}'.format(job_name),
                                '--output={}'.format(output_log),
                                '--error={}'.format(error_log),
                                '--mem=8000',
                                '-p', 'wmglab',
                                '-c', '1',
                                start_path
                            ])
                            os.system(command)

                            # allow job to start before removing slurm file
                            time.sleep(1.0)

                            # remove start.slurm
                            os.remove(start_path)

                        elif submission_context == 'local':
                            local_args['start_path'] = start_path
                            local_args['output_log'] = output_log
                            local_args['error_log'] = error_log

                            local_args_list.append(local_args.copy())

        return local_args_list

        # number_processes = 2
        # pool = multiprocessing.Pool(number_processes)
        # results = pool.map_async(local_submit, local_args_list)
        # results.wait()
        # results.get()
        # pool.close()
        # pool.join()

        # local_submit(local_args_list)

        # my_filename = local_args_list[0]['start_path']
        # my_output_log = local_args_list[0]['output_log']
        # my_error_log = local_args_list[0]['error_log']
        #
        # # p = subprocess.Popen(bat, cwd=sim_path)
        # print(os.getcwd())
        # os.chdir("D:\\Documents\\ascent\\submit\\n_sims\\1003_0_1005_0")
        # print(os.getcwd())
        # # p = subprocess.Popen(["D:\\Documents\\ascent\\submit\\n_sims\\1003_0_1005_0\\example.bat"])
        # p = subprocess.Popen(["example.bat"])

    # stdout, stderr = p.communicate()
    # p.wait()

    # THIS WORKED
    # print('here')
    # if __name__ == '__main__':
    #     p = Process(target=local_submit, args=('bob',))
    #     p.start()
    #     p.join()

    # subprocess.call(my_filename)

    # if OS is 'UNIX-LIKE':
    #     subprocess.run(['chmod', '777', os.path.join(os.path.split(my_filename)[0], 'blank.hoc')], shell=False)
    #     subprocess.run(['chmod', '777', my_filename], shell=False)
    # run_command = ['bash', my_filename, 'stdout', my_output_log, 'stderr', my_error_log, 'capture_output=True']
    # #run_command = ['bash', my_filename, 'stdout', my_output_log, 'stderr', my_error_log, 'capture_output=True']


def local_submit(my_local_args):
    my_filename = my_local_args['start_path']
    # my_output_log = local_args_list[0]['output_log']
    # my_error_log = local_args_list[0]['error_log']
    print(my_filename)

    # p = subprocess.Popen(bat, cwd=sim_path)
    os.chdir("D:\\Documents\\ascent\\submit\\n_sims\\1003_0_1005_0")
    # p = subprocess.Popen(["example.bat"])
    out_filename = "out_inner0_fiber0.log"
    err_filename = "err_inner0_fiber0.log"

    with open(out_filename, "w+") as fo, open(err_filename, "w+") as fe:
        p = subprocess.call(["0_0_start.bat"],
                            stdout=fo,
                            stderr=fe)
        # p = subprocess.call(["0_0_start.bat"])
        # p.wait()


# my_filename = my_local_args['start_path']
# my_output_log = my_local_args['output_log']
# my_error_log = my_local_args['error_log']
#
# if OS is 'UNIX-LIKE':
#     subprocess.run(['chmod', '777', os.path.join(os.path.split(my_filename)[0], 'blank.hoc')], shell=False)
#     subprocess.run(['chmod', '777', my_filename], shell=False)
# run_command = ['bash', my_filename, 'stdout', my_output_log, 'stderr', my_error_log, 'capture_output=True']
# #run_command = ['bash', my_filename, 'stdout', my_output_log, 'stderr', my_error_log, 'capture_output=True']
#
# return subprocess.call(run_command[1:])


def main():
    submit_list = make_submission_list()
    pool = multiprocessing.Pool(multiprocessing.cpu_count())
    result = pool.map(local_submit, [submit_list[0]])


if __name__ == "__main__":  # Allows for the safe importing of the main module
    main()

    # threads = []
    # num_processes = 2
    # print("There are %d CPUs on this machine" % multiprocessing.cpu_count())
    #
    # while threads or local_args_list:
    #     # if we aren't using all the processors AND there is still data left to
    #     # compute, then spawn another thread
    #     if (len(threads) < num_processes) and local_args_list:
    #         t = threading.Thread(target=local_submit, args=[local_args_list.pop(0)])
    #         t.setDaemon(True)
    #         t.start()
    #         threads.append(t)
    #
    #     # in the case that we have the maximum number of threads check if any of them
    #     # are done. (also do this when we run out of data, until all the threads are done)
    #     else:
    #         for thread in threads:
    #             if not thread.is_alive():
    #                 threads.remove(thread)

    # print("There are %d CPUs on this machine" % multiprocessing.cpu_count())
    # number_processes = 2
    # pool = multiprocessing.Pool(number_processes)
    # total_tasks = 16
    # tasks = range(total_tasks)
    # results = pool.map_async(work, tasks)
    # pool.close()
    # pool.join()
