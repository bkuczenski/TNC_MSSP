from MSSP.utils import defaultdir

json_parts = ('colormap', 'questions', 'targets', 'criteria', 'caveats', 'attributes', 'notes')


def write_json(json_out, outdir=None, outfile=None):
    """
    Routine to write json output to file(s)
    :param json_out: the output of serialize()
    :param outdir: directory name (absolute, or relative to defaultdir) to use for writing files.
    :param outfile: (None) whether to write all content to a single json file (default: false)
    :return:
    """
    import os
    import json
    onefile = True

    if outfile is None:
        onefile = False

    if outdir is None:
        write_dir = os.path.join(defaultdir, 'JSON_OUT')
    else:
        if os.path.isabs(outdir):
            write_dir = outdir
        else:
            write_dir = os.path.join(defaultdir, outdir)

    if not os.path.exists(write_dir):
        os.makedirs(write_dir)

    if onefile:
        write_file = os.path.join(write_dir, outfile)
        f = open(write_file, mode='w')
        f.write(json.dumps(json_out, indent=4))
        f.close()
        print "Output written as {0}.".format(write_file)
    else:
        for i in json_parts:
            f = open(os.path.join(write_dir, i + '.json'), mode='w')
            json.dump(json_out[i], f, indent=4)
            f.close()
        print "Output written to folder {0}.".format(write_dir)

    return True


def read_json(json_in):
    """

    :param json_in: pointer to directory or file
    :return: mssp_engine object in JSON serialized form
    """
    import os
    import json

    if os.path.isabs(json_in):
        read_path = json_in
    else:
        read_path = os.path.join(defaultdir, json_in)

    if not os.path.exists(read_path):
        raise IOError("File not found: {0}".format(read_path))

    if os.path.isdir(read_path):
        json_out = {}
        for f in json_parts:
            fp = open(os.path.join(read_path, f + '.json'), mode='r')
            json_out[f] = json.load(fp)
            fp.close()
    else:
        fp = open(read_path, mode='r')
        json_out = json.load(fp)
        fp.close()

    return json_out
