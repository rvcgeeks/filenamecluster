"""Tests for the data-folder stand-in script."""

from pathlib import Path

import pytest

import stub

LISTING = Path(__file__).resolve().parents[1] / "filenames.txt"

DIR_LISTING = """ Volume in drive D is Data

24-11-2025  02:04    <DIR>          .
24-11-2025  02:04    <DIR>          ..
19-07-2020  01:07    <DIR>          a
29-09-2024  19:25                 0 .escheck.tmp
10-05-2016  12:21           525,509 2016-05-10-12-21-48-870.jpg
            2 File(s) 1 bytes
"""

LS_LISTING = """total 8
-rw-r--r--  1 user staff  12 Jan  2  2024 old photo.jpg
drwxr-xr-x  2 user staff  64 Sep 27 00:11 sub
lrwxr-xr-x  1 user staff  10 Sep 27 00:11 link.jpg -> empty.jpg
"""


def test_create_from_dir_listing(tmp_path: Path) -> None:
    listing = tmp_path / "filenames.txt"
    listing.write_text(DIR_LISTING, encoding="utf-8")
    stub.create_files(str(listing), tmp_path)

    created = tmp_path / "2016-05-10-12-21-48-870.jpg"
    assert created.is_file()
    assert created.stat().st_size == 0
    assert (tmp_path / ".escheck.tmp").is_file()
    assert not (tmp_path / "a").exists()
    assert listing.read_text(encoding="utf-8") == DIR_LISTING


def test_create_from_ls_and_plain_names(tmp_path: Path) -> None:
    listing = tmp_path / "ls.txt"
    listing.write_text(LS_LISTING, encoding="utf-8")
    stub.create_files(str(listing), tmp_path)
    assert (tmp_path / "old photo.jpg").is_file()
    assert (tmp_path / "link.jpg").is_file()
    assert not (tmp_path / "sub").exists()
    assert (tmp_path / "old photo.jpg").stat().st_size == 0

    plain = tmp_path / "plain.txt"
    plain.write_text("IMG_20240101_100000.jpg\nmy photo.jpg\n\n.\n", encoding="utf-8")
    stub.create_files(str(plain), tmp_path)
    assert (tmp_path / "IMG_20240101_100000.jpg").is_file()
    assert (tmp_path / "my photo.jpg").is_file()


def test_create_leaves_existing_files(tmp_path: Path) -> None:
    photo = tmp_path / "keep.jpg"
    photo.write_text("real", encoding="utf-8")
    listing = tmp_path / "names.txt"
    listing.write_text("keep.jpg\nnew.jpg\n", encoding="utf-8")
    stub.create_files(str(listing), tmp_path)
    assert photo.read_text(encoding="utf-8") == "real"
    assert (tmp_path / "new.jpg").stat().st_size == 0


def test_clean_keeps_filled_files_and_their_folders(tmp_path: Path) -> None:
    keep = tmp_path / "keep"
    keep.mkdir()
    (keep / "filled.jpg").write_text("content", encoding="utf-8")
    (keep / "empty.jpg").touch()
    (tmp_path / "top-filled.jpg").write_text("content", encoding="utf-8")
    (tmp_path / "loose.jpg").touch()
    (tmp_path / "filenames.txt").write_text("listing\n", encoding="utf-8")
    nested = tmp_path / "empty-dir" / "nested"
    nested.mkdir(parents=True)

    stub.clean_empty(tmp_path)

    assert (keep / "filled.jpg").read_text(encoding="utf-8") == "content"
    assert (tmp_path / "top-filled.jpg").is_file()
    assert (tmp_path / "filenames.txt").is_file()
    assert not (keep / "empty.jpg").exists()
    assert not (tmp_path / "loose.jpg").exists()
    assert not (tmp_path / "empty-dir").exists()
    assert keep.is_dir()


def test_cli_resolves_the_listing_beside_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(stub, "PROJECT", tmp_path)
    monkeypatch.setattr(stub, "DATA", data)
    (tmp_path / "filenames.txt").write_text("shot.jpg\n", encoding="utf-8")
    assert stub.main(["create", "filenames.txt"]) == 0
    assert (data / "shot.jpg").is_file()
    assert not (tmp_path / "shot.jpg").exists()
    assert stub.main(["clean"]) == 0
    assert not (data / "shot.jpg").exists()
    assert (tmp_path / "filenames.txt").is_file()


def test_missing_listing_exits(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        stub.create_files("missing.txt", tmp_path)


def test_camera_roll_listing_parses_without_creating_files() -> None:
    lines = LISTING.read_text(encoding="utf-8-sig").splitlines()
    names, ignored_dirs, mode = stub._names_from_listing(lines)
    assert mode == "dir"
    assert ignored_dirs == 4
    assert len(names) == 11484
    assert "BeautyPlus_20160406180905_save.jpg" in names
    assert not any("marksheet" in name or "scholarship" in name for name in names)
    assert "InShot_20240127_220124404.mp4" in names
    assert "Project_12_02_2023-12-03-01-32-06.mp4" in names
    assert "PhotoGrid_1581064265269.jpg" in names
    assert "IMG-20170610-WA0005.jpg" in names
    assert "VID-20231230-WA0013.mp4" in names
    assert "Screenshot_2019-08-14-09-26-13-264_lockscreen.png" in names
    assert "IMG_20200317_150503_BURST1.jpg" in names
    assert "VID_20201116_172025_HSR_120.mp4" in names
    assert "VID_20210401_142601_exported_16951.jpg" in names
    assert "IMG_20210526_214754_HHT.jpg" in names
    assert "20200101_001000.mp4" in names
    assert "img1462863402727.jpg" in names
    assert "CamScanner 11-21-2024 12.22.jpg" in names
