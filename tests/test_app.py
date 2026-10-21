"""Testes offline: nao fazem download de nenhum video real."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as website


class TestVibeDrop(unittest.TestCase):
    def setUp(self):
        self.client = website.app.test_client()
        self.old_code = website.ACCESS_CODE
        website.ACCESS_CODE = ''
        self.tmp_dirs = []
        with website.lock:
            website.jobs.clear()
            website.client_cooldowns.clear()
            website.previews.clear()
            website.login_attempts.clear()

    def tearDown(self):
        website.ACCESS_CODE = self.old_code
        with website.lock:
            for job in website.jobs.values():
                website.shutil.rmtree(job.folder, ignore_errors=True)
            website.jobs.clear()
            website.client_cooldowns.clear()
            website.previews.clear()
            website.login_attempts.clear()
        for temp in self.tmp_dirs:
            temp.cleanup()

    def test_supported_platforms(self):
        cases = {
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=14': ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'YouTube'),
            'https://youtu.be/dQw4w9WgXcQ': ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'YouTube'),
            'https://www.youtube.com/shorts/dQw4w9WgXcQ': ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'YouTube'),
            'https://www.instagram.com/reel/ABC123defGh/?utm_source=ig': ('https://www.instagram.com/reel/ABC123defGh/', 'Instagram'),
            'https://www.instagram.com/p/ABC123defGh/': ('https://www.instagram.com/p/ABC123defGh/', 'Instagram'),
            'https://www.tiktok.com/@criador/video/7381990233232203009': ('https://www.tiktok.com/@criador/video/7381990233232203009', 'TikTok'),
            'https://vm.tiktok.com/ZSABC123/': ('https://vm.tiktok.com/ZSABC123/', 'TikTok'),
        }
        for src, expected in cases.items():
            with self.subTest(src=src):
                self.assertEqual(website.normalize_media_link(src), expected)

    def test_invalid_links_are_blocked(self):
        invalid = [
            'http://youtu.be/dQw4w9WgXcQ', 'https://localhost/private',
            'https://127.0.0.1/private', 'https://evil.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtube.com.evil.com/watch?v=dQw4w9WgXcQ',
            'https://www.youtube.com/playlist?list=PL123',
            'https://www.instagram.com/fulano/',
            'https://www.tiktok.com/@user',
            'https://www.youtube.com:443/watch?v=dQw4w9WgXcQ',
            'https://www.youtube.com/%2F/watch?v=dQw4w9WgXcQ',
            'https://www.youtube.com/watch?v=oops',
            'javascript:alert(1)',
        ]
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                website.normalize_media_link(raw)

    def test_html_and_health(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="video-tab"', response.data)
        self.assertIn(b'id="audio-tab"', response.data)
        self.assertEqual(self.client.get('/health').json['status'], 'ok')

    def test_bad_job_requests(self):
        invalid = [
            {'url': 'https://localhost', 'format': 'mp4'},
            {'url': 'https://youtu.be/dQw4w9WgXcQ', 'format': 'wav'},
            {'url': 'https://youtu.be/dQw4w9WgXcQ', 'format': 'mp4', 'quality': '9999'},
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post('/api/jobs', json=payload).status_code, 400)

    def test_video_job_and_download(self):
        with patch.object(website.executor, 'submit') as submit:
            response = self.client.post('/api/jobs', json={
                'url': 'https://www.tiktok.com/@creator/video/7381990233232203009',
                'format': 'mp4', 'quality': '720',
            })
            self.assertEqual(response.status_code, 202)
            submit.assert_called_once()
        job = website.jobs[response.json['job_id']]
        self.assertEqual((job.platform, job.fmt, job.quality), ('TikTok', 'mp4', '720'))
        self.assertIn('height<=720', website.media_options(job, lambda _: None)['format'])
        out = job.folder / 'media.mp4'
        out.write_bytes(b'fake mp4')
        website.update_job(job, status='ready', percent=100, file_path=out,
                           filename='Teste de video.mp4', ended=website.time.time())
        result = self.client.get(f'/api/jobs/{job.id}/download')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data, b'fake mp4')
        self.assertEqual(result.mimetype, 'video/mp4')

    def test_six_hour_media_no_duration_limit(self):
        tmp = tempfile.TemporaryDirectory()
        self.tmp_dirs.append(tmp)
        job = website.Job('long', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                          'mp3', Path(tmp.name), website.time.time(), platform='YouTube')
        outer = self

        class FakeDL:
            def __init__(self, options): self.options = options
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def extract_info(self, url, download):
                outer.assertIsNone(self.options['match_filter']({
                    'duration': 6 * 3600, 'is_live': False,
                }))
                job.folder.joinpath('media.mp3').write_bytes(b'fake audio')
                return {'title': 'Audio autorizado de 6h', 'duration': 6 * 3600}

        with patch.object(website.yt_dlp, 'YoutubeDL', FakeDL), patch.object(website, 'check_free_space'):
            website.download_job(job)
        self.assertEqual(job.status, 'ready')
        self.assertEqual(job.filename, 'Audio autorizado de 6h.mp3')

    def test_no_global_hourly_limit_and_fair_cooldown(self):
        """Não há cota global; usuários têm pausa individual após o processamento."""
        payload = {'url': 'https://youtu.be/dQw4w9WgXcQ', 'format': 'm4a'}
        with patch.object(website.executor, 'submit'):
            one = self.client.post('/api/jobs', json=payload)
            self.assertEqual(one.status_code, 202)
            first = website.jobs[one.json['job_id']]
            website.update_job(first, status='error', ended=website.time.time())
            blocked = self.client.post('/api/jobs', json=payload)
            self.assertEqual(blocked.status_code, 429)
            self.assertIn('Aguarde', blocked.json['error'])
            other = website.app.test_client()
            two = other.post('/api/jobs', json=payload)
            self.assertEqual(two.status_code, 202)
            second = website.jobs[two.json['job_id']]
            self.assertEqual(self.client.get('/api/jobs/' + second.id).status_code, 404)
            self.assertEqual(self.client.get('/api/jobs/' + second.id + '/download').status_code, 404)
            website.update_job(second, status='error', ended=website.time.time())
            with website.lock:
                website.client_cooldowns.clear()
            three = self.client.post('/api/jobs', json=payload)
            self.assertEqual(three.status_code, 202)
            website.update_job(website.jobs[three.json['job_id']], status='error', ended=website.time.time())

    def test_370mb_limit_without_duration_limit(self):
        with patch.object(website, 'MAX_FILE_BYTES', 370 * 1024 * 1024):
            with tempfile.TemporaryDirectory() as folder:
                job = website.Job('limit', 'https://youtu.be/dQw4w9WgXcQ', 'mp4',
                                  Path(folder), website.time.time())
                opts = website.media_options(job, lambda _: None)
                self.assertEqual(opts['max_filesize'], 370 * 1024 * 1024)
                self.assertIsNone(opts['match_filter']({'duration': 3 * 3600, 'is_live': False}))

    def test_preview_without_real_internet(self):
        class FakeDL:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def extract_info(self, url, download):
                return {'title': 'Vídeo teste', 'duration': 630, 'thumbnail': 'https://i.ytimg.com/test.jpg'}
        with patch.object(website.yt_dlp, 'YoutubeDL', FakeDL):
            result = self.client.post('/api/preview', json={
                'url': 'https://www.instagram.com/reel/ABC123defGh/'
            })
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['platform'], 'Instagram')
        self.assertEqual(result.json['duration'], 630)
        self.assertEqual(result.json['thumbnail'], 'https://i.ytimg.com/test.jpg')
        self.assertIsNone(website.safe_thumbnail('https://127.0.0.1/secret'))

    def test_password_protection(self):
        website.ACCESS_CODE = 'senha-teste'
        self.assertEqual(self.client.get('/').status_code, 302)
        self.assertEqual(self.client.get('/api/jobs/id').status_code, 401)
        self.assertEqual(self.client.post('/login', data={'code': 'errada'}).status_code, 200)
        self.assertEqual(self.client.post('/login', data={'code': 'senha-teste'}).status_code, 302)
        self.assertEqual(self.client.get('/').status_code, 200)


if __name__ == '__main__':
    unittest.main()
