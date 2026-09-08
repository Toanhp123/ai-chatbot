"""
Bộ kiểm thử toàn diện cho hệ thống Dataset & Batch Providers (dataset.py).
Đảm bảo TextDataset, MemmapDataset (O(1) RAM), TensorBatchProvider, DataLoaderBatchProvider,
và factory get_batch_provider.
"""

import os

import pytest
import torch
from torch.utils.data import Dataset

from src.core.config import DataConfig
from src.core.exceptions import DataPipelineError, DatasetEmptyError
from src.data.batch_provider import (
    BaseBatchProvider,
    DataLoaderBatchProvider,
    TensorBatchProvider,
    get_batch_provider,
)
from src.data.cleaners import TextCleaner
from src.data.dataset import (
    MemmapDataset,
    TextDataset,
)
from src.data.pipeline import DataPipeline
from src.data.tokenizers import BaseTokenizer


def test_text_dataset_indexing():
    data = torch.arange(100, dtype=torch.long)
    ds = TextDataset(data, block_size=10)

    assert isinstance(ds, Dataset)
    assert len(ds) == 90
    x, y = ds[0]
    assert len(x) == 10 and len(y) == 10
    assert torch.equal(x, torch.arange(0, 10))
    assert torch.equal(y, torch.arange(1, 11))


def test_text_dataset_empty_error():
    data = torch.arange(5, dtype=torch.long)
    with pytest.raises(DatasetEmptyError) as exc_info:
        TextDataset(data, block_size=10)
    assert "ngắn hơn hoặc bằng độ dài ngữ cảnh" in str(exc_info.value)


def test_tensor_batch_provider():
    train_data = torch.arange(1000, dtype=torch.long)
    val_data = torch.arange(200, dtype=torch.long)
    provider = TensorBatchProvider(train_data, val_data)

    assert isinstance(provider, BaseBatchProvider)
    assert provider.train_tokens == 1000
    assert provider.val_tokens == 200

    x, y = provider.get_train_batch(batch_size=4, block_size=16, device="cpu")
    assert x.shape == (4, 16)
    assert y.shape == (4, 16)

    x_val, y_val = provider.get_val_batch(batch_size=2, block_size=8, device="cpu")
    assert x_val.shape == (2, 8)
    assert y_val.shape == (2, 8)


def test_tensor_batch_provider_empty_error():
    provider = TensorBatchProvider(torch.arange(5), torch.arange(5))
    with pytest.raises(DatasetEmptyError):
        provider.get_train_batch(batch_size=2, block_size=10, device="cpu")


def test_dataloader_batch_provider():
    train_ds = TextDataset(torch.arange(200, dtype=torch.long), block_size=8)
    val_ds = TextDataset(torch.arange(100, dtype=torch.long), block_size=8)

    dl_provider = DataLoaderBatchProvider(
        train_dataset=train_ds,
        val_dataset=val_ds,
        num_workers=0,
        pin_memory=False,
    )

    assert isinstance(dl_provider, BaseBatchProvider)

    for _ in range(5):
        x, y = dl_provider.get_train_batch(batch_size=4, block_size=8, device="cpu")
        assert x.shape == (4, 8)
        assert y.shape == (4, 8)

    x_val, y_val = dl_provider.get_val_batch(batch_size=2, block_size=8, device="cpu")
    assert x_val.shape == (2, 8)
    assert y_val.shape == (2, 8)


def test_get_batch_provider_factory():
    train_data = torch.arange(200, dtype=torch.long)
    val_data = torch.arange(100, dtype=torch.long)

    p_tensor = get_batch_provider("tensor", train_data, val_data, block_size=8)
    assert isinstance(p_tensor, TensorBatchProvider)

    p_dl = get_batch_provider("dataloader", train_data, val_data, block_size=8)
    assert isinstance(p_dl, DataLoaderBatchProvider)

    with pytest.raises(DataPipelineError):
        get_batch_provider("invalid_provider", train_data, val_data)


def test_memmap_dataset_and_binary_io(tmp_path):
    bin_file = str(tmp_path / "tokens.bin")
    tokens = torch.randint(0, 200, (500,), dtype=torch.long)

    DataPipeline.save_to_binary(tokens, bin_file, dtype="uint16")
    assert os.path.exists(bin_file)

    mem_ds = MemmapDataset(bin_file, block_size=16, dtype="uint16")
    assert isinstance(mem_ds, Dataset)
    assert len(mem_ds) == 500 - 16

    x, y = mem_ds[0]
    assert x.shape == (16,)
    assert y.shape == (16,)
    assert torch.equal(x, tokens[:16])
    assert torch.equal(y, tokens[1:17])

    loaded_tensor = DataPipeline.load_binary(bin_file, dtype="uint16")
    assert torch.equal(loaded_tensor, tokens)

    with pytest.raises(DataPipelineError):
        MemmapDataset("non_existent.bin", block_size=16)


def test_data_pipeline_setup_data(tmp_path):
    config = DataConfig(
        data_dir=str(tmp_path / "data"),
        input_file=str(tmp_path / "data" / "input.txt"),
        vocab_file=str(tmp_path / "data" / "vocab.json"),
        split_ratio=0.8,
        clean_line_numbers=True,
    )

    cleaner = TextCleaner(clean_line_numbers=True)
    train_data, val_data, tokenizer = DataPipeline.setup_data(config, cleaner=cleaner)

    assert len(train_data) > 0
    assert len(val_data) > 0
    assert tokenizer.vocab_size > 0
    assert isinstance(tokenizer, BaseTokenizer)

    assert os.path.exists(config.input_file)
    assert os.path.exists(config.vocab_file)


def test_data_pipeline_creates_input_file_parent_directory(tmp_path):
    """input_file may live outside data_dir and its parent must still be created."""
    input_file = tmp_path / "nested" / "corpus" / "input.txt"
    config = DataConfig(
        data_dir=str(tmp_path / "data"),
        input_file=str(input_file),
        vocab_file=str(tmp_path / "data" / "vocab.json"),
    )

    text = DataPipeline.fetch_or_load_text(config, cleaner=TextCleaner())

    assert text
    assert input_file.exists()


@pytest.mark.parametrize("operation", ["save", "load", "memmap"])
def test_binary_data_rejects_unknown_numpy_dtype(tmp_path, operation: str):
    """Unknown dtypes must not silently fall back to uint16 and reinterpret data."""
    bin_file = str(tmp_path / "tokens.bin")
    torch.arange(32, dtype=torch.long).numpy().astype("uint16").tofile(bin_file)

    with pytest.raises(DataPipelineError, match="dtype"):
        if operation == "save":
            DataPipeline.save_to_binary(torch.arange(32), bin_file, dtype="not_a_dtype")
        elif operation == "load":
            DataPipeline.load_binary(bin_file, dtype="not_a_dtype")
        else:
            MemmapDataset(bin_file, block_size=4, dtype="not_a_dtype")


@pytest.mark.parametrize("dtype", ["float32", "bool"])
def test_binary_token_storage_rejects_non_integer_dtype(tmp_path, dtype: str) -> None:
    with pytest.raises(DataPipelineError, match="integer"):
        DataPipeline.save_to_binary(torch.arange(8), str(tmp_path / "tokens.bin"), dtype=dtype)


def test_binary_token_storage_rejects_values_outside_dtype_range(tmp_path) -> None:
    tokens = torch.tensor([0, 65_535, 65_536], dtype=torch.long)
    with pytest.raises(DataPipelineError, match="range"):
        DataPipeline.save_to_binary(tokens, str(tmp_path / "tokens.bin"), dtype="uint16")
