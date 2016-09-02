class Settings(object):
    def __init__(self, *args, **kwargs):
        self.use_binary_prefix = True
        self.use_bits = False

        self.bandwidth_max_download_per_sec = None
        self.bandwidth_max_upload_per_sec = None

        self.status_icon_max_download_per_sec = None
        self.status_icon_max_upload_per_sec = None
        self.status_icon_bgcolor = (0, 0, 0)
        self.status_icon_download_color = (1, 0, 0)
        self.status_icon_upload_color = (0, 1, 0)

    def as_dict(self):
        return {
            'use_binary_prefix': self.use_binary_prefix,
            'use_bits': self.use_bits
        }

    def as_json(self):
        import json
        return json.dumps(self.as_dict())
