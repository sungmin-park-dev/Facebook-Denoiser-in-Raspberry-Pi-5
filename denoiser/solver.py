# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
# author: adiyoss

import json
import logging
from pathlib import Path
import os
import time

import torch
import torch.nn.functional as F

# ========================================
# ✅ 추가: Loss 그래프를 위한 import
# ========================================
import matplotlib
matplotlib.use('Agg')  # Colab/서버 환경 호환
import matplotlib.pyplot as plt

from . import augment, distrib, pretrained
from .enhance import enhance
from .evaluate import evaluate
from .stft_loss import MultiResolutionSTFTLoss
from .utils import bold, copy_state, pull_metric, serialize_model, swap_state, LogProgress

logger = logging.getLogger(__name__)


class Solver(object):
    def __init__(self, data, model, optimizer, args):
        self.tr_loader = data['tr_loader']
        self.cv_loader = data['cv_loader']
        self.tt_loader = data['tt_loader']
        self.model = model
        self.dmodel = distrib.wrap(model)
        self.optimizer = optimizer

        # data augment
        augments = []
        if args.remix:
            augments.append(augment.Remix())
        if args.bandmask:
            augments.append(augment.BandMask(args.bandmask, sample_rate=args.sample_rate))
        if args.shift:
            augments.append(augment.Shift(args.shift, args.shift_same))
        if args.revecho:
            augments.append(
                augment.RevEcho(args.revecho))
        self.augment = torch.nn.Sequential(*augments)

        # Training config
        self.device = args.device
        self.epochs = args.epochs

        # Checkpoints
        self.continue_from = args.continue_from
        self.eval_every = args.eval_every
        self.checkpoint = args.checkpoint
        if self.checkpoint:
            self.checkpoint_file = Path(args.checkpoint_file)
            self.best_file = Path(args.best_file)
            logger.debug("Checkpoint will be saved to %s", self.checkpoint_file.resolve())
        self.history_file = args.history_file

        self.best_state = None
        self.restart = args.restart
        self.history = []  # Keep track of loss
        self.samples_dir = args.samples_dir  # Where to save samples
        self.num_prints = args.num_prints  # Number of times to log per epoch
        self.args = args
        self.mrstftloss = MultiResolutionSTFTLoss(factor_sc=args.stft_sc_factor,
                                                  factor_mag=args.stft_mag_factor).to(self.device)
        
        # ========================================
        # ✅ 추가: Loss history 저장용 리스트
        # ========================================
        self.loss_history = {
            'train': [],  # 매 epoch의 train loss
            'valid': []   # 매 epoch의 valid loss
        }
        
        self._reset()

    def _serialize(self):
        package = {}
        package['model'] = serialize_model(self.model)
        package['optimizer'] = self.optimizer.state_dict()
        package['history'] = self.history
        package['best_state'] = self.best_state
        package['args'] = self.args
        
        # ========================================
        # ✅ 추가: loss_history도 checkpoint에 저장
        # ========================================
        package['loss_history'] = self.loss_history
        
        tmp_path = str(self.checkpoint_file) + ".tmp"
        torch.save(package, tmp_path)
        # renaming is sort of atomic on UNIX (not really true on NFS)
        # but still less chances of leaving a half written checkpoint behind.
        os.rename(tmp_path, self.checkpoint_file)

        # Saving only the latest best model.
        model = package['model']
        model['state'] = self.best_state
        tmp_path = str(self.best_file) + ".tmp"
        torch.save(model, tmp_path)
        os.rename(tmp_path, self.best_file)

    def _reset(self):
        """_reset."""
        load_from = None
        load_best = False
        keep_history = True
        # Reset
        if self.checkpoint and self.checkpoint_file.exists() and not self.restart:
            load_from = self.checkpoint_file
        elif self.continue_from:
            load_from = self.continue_from
            load_best = self.args.continue_best
            keep_history = False

        if load_from:
            logger.info(f'Loading checkpoint model: {load_from}')
            package = torch.load(load_from, 'cpu')
            if load_best:
                self.model.load_state_dict(package['best_state'])
            else:
                self.model.load_state_dict(package['model']['state'])
            if 'optimizer' in package and not load_best:
                self.optimizer.load_state_dict(package['optimizer'])
            if keep_history:
                self.history = package['history']
                
                # ========================================
                # ✅ 추가: checkpoint에서 loss_history 복원
                # ========================================
                if 'loss_history' in package:
                    self.loss_history = package['loss_history']
                    
            self.best_state = package['best_state']
        continue_pretrained = self.args.continue_pretrained
        if continue_pretrained:
            logger.info("Fine tuning from pre-trained model %s", continue_pretrained)
            model = getattr(pretrained, self.args.continue_pretrained)()
            self.model.load_state_dict(model.state_dict())

    # ========================================
    # ✅ 추가: Loss 그래프 생성 함수
    # ========================================
    def _plot_loss(self, epoch):
        """
        Loss 그래프를 생성하고 파일로 저장
        - Colab에서도 작동하도록 정적 이미지로 저장
        - 매번 새로운 그래프 생성 (업데이트 없음)
        """
        try:
            # 출력 디렉토리 확인
            output_dir = Path(self.args.samples_dir).parent
            output_dir.mkdir(exist_ok=True, parents=True)
            
            # 그래프 생성
            plt.figure(figsize=(12, 5))
            
            # Train Loss
            epochs_range = list(range(1, len(self.loss_history['train']) + 1))
            plt.subplot(1, 2, 1)
            plt.plot(epochs_range, self.loss_history['train'], 'b-', linewidth=2, marker='o')
            plt.xlabel('Epoch', fontsize=12)
            plt.ylabel('Train Loss', fontsize=12)
            plt.title(f'Training Loss (Current: {self.loss_history["train"][-1]:.5f})', fontsize=14)
            plt.grid(True, alpha=0.3)
            
            # Valid Loss (있는 경우)
            if self.loss_history['valid'] and any(v > 0 for v in self.loss_history['valid']):
                plt.subplot(1, 2, 2)
                plt.plot(epochs_range, self.loss_history['valid'], 'r-', linewidth=2, marker='s')
                plt.xlabel('Epoch', fontsize=12)
                plt.ylabel('Valid Loss', fontsize=12)
                plt.title(f'Validation Loss (Current: {self.loss_history["valid"][-1]:.5f})', fontsize=14)
                plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # 파일로 저장 (epoch별로 별도 파일)
            plot_path = output_dir / f'loss_epoch_{epoch+1:03d}.png'
            plt.savefig(plot_path, dpi=100, bbox_inches='tight')
            logger.info(f"📊 Loss plot saved: {plot_path}")
            
            # 최신 그래프는 항상 'loss_latest.png'로도 저장
            latest_path = output_dir / 'loss_latest.png'
            plt.savefig(latest_path, dpi=100, bbox_inches='tight')
            
            plt.close()
            
            # ========================================
            # ✅ Colab 환경이면 이미지 표시
            # ========================================
            try:
                from IPython.display import Image, display
                import IPython
                if 'google.colab' in str(IPython.get_ipython()):
                    display(Image(filename=str(latest_path)))
                    logger.info("✅ Graph displayed in Colab")
            except:
                pass  # Colab 아니면 스킵
                
        except Exception as e:
            logger.warning(f"❌ Failed to plot loss: {e}")

    def train(self):
        if self.args.save_again:
            self._serialize()
            return
        # Optimizing the model
        if self.history:
            logger.info("Replaying metrics from previous run")
        for epoch, metrics in enumerate(self.history):
            info = " ".join(f"{k.capitalize()}={v:.5f}" for k, v in metrics.items())
            logger.info(f"Epoch {epoch + 1}: {info}")

        for epoch in range(len(self.history), self.epochs):
            # Train one epoch
            self.model.train()
            start = time.time()
            logger.info('-' * 70)
            logger.info("Training...")
            train_loss = self._run_one_epoch(epoch)
            logger.info(
                bold(f'Train Summary | End of Epoch {epoch + 1} | '
                     f'Time {time.time() - start:.2f}s | Train Loss {train_loss:.5f}'))

            # ========================================
            # ✅ 추가: Train loss 저장
            # ========================================
            self.loss_history['train'].append(train_loss)

            if self.cv_loader:
                # Cross validation
                logger.info('-' * 70)
                logger.info('Cross validation...')
                self.model.eval()
                with torch.no_grad():
                    valid_loss = self._run_one_epoch(epoch, cross_valid=True)
                logger.info(
                    bold(f'Valid Summary | End of Epoch {epoch + 1} | '
                         f'Time {time.time() - start:.2f}s | Valid Loss {valid_loss:.5f}'))
            else:
                valid_loss = 0

            # ========================================
            # ✅ 추가: Valid loss 저장
            # ========================================
            self.loss_history['valid'].append(valid_loss)

            best_loss = min(pull_metric(self.history, 'valid') + [valid_loss])
            metrics = {'train': train_loss, 'valid': valid_loss, 'best': best_loss}
            # Save the best model
            if valid_loss == best_loss:
                logger.info(bold('New best valid loss %.4f'), valid_loss)
                self.best_state = copy_state(self.model.state_dict())

            # ========================================
            # ✅ 추가: 5 epoch마다 Loss 그래프 생성
            # ========================================
            if (epoch + 1) % 5 == 0:
                logger.info("=" * 70)
                logger.info(f"📊 Generating loss plot at Epoch {epoch + 1}")
                self._plot_loss(epoch)
                logger.info("=" * 70)

            # evaluate and enhance samples every 'eval_every' argument number of epochs
            # also evaluate on last epoch
            if ((epoch + 1) % self.eval_every == 0 or epoch == self.epochs - 1) and self.tt_loader:
                # Evaluate on the testset
                logger.info('-' * 70)
                logger.info('Evaluating on the test set...')
                # We switch to the best known model for testing
                with swap_state(self.model, self.best_state):
                    pesq, stoi = evaluate(self.args, self.model, self.tt_loader)

                metrics.update({'pesq': pesq, 'stoi': stoi})
                
                # ========================================
                # ✅ 추가: PESQ/STOI 로그 강조 표시
                # ========================================
                logger.info("=" * 70)
                logger.info(f"🎯 Test Metrics at Epoch {epoch + 1}")
                logger.info(f"   PESQ: {pesq:.4f}")
                logger.info(f"   STOI: {stoi:.4f}")
                logger.info("=" * 70)

                # enhance some samples
                logger.info('Enhance and save samples...')
                enhance(self.args, self.model, self.samples_dir)

            self.history.append(metrics)
            info = " | ".join(f"{k.capitalize()} {v:.5f}" for k, v in metrics.items())
            logger.info('-' * 70)
            logger.info(bold(f"Overall Summary | Epoch {epoch + 1} | {info}"))

            if distrib.rank == 0:
                json.dump(self.history, open(self.history_file, "w"), indent=2)
                # Save model each epoch
                if self.checkpoint:
                    self._serialize()
                    logger.debug("Checkpoint saved to %s", self.checkpoint_file.resolve())

    def _run_one_epoch(self, epoch, cross_valid=False):
        total_loss = 0
        data_loader = self.tr_loader if not cross_valid else self.cv_loader

        # get a different order for distributed training, otherwise this will get ignored
        data_loader.epoch = epoch

        label = ["Train", "Valid"][cross_valid]
        name = label + f" | Epoch {epoch + 1}"
        logprog = LogProgress(logger, data_loader, updates=self.num_prints, name=name)
        for i, data in enumerate(logprog):
            noisy, clean = [x.to(self.device) for x in data]
            if not cross_valid:
                sources = torch.stack([noisy - clean, clean])
                sources = self.augment(sources)
                noise, clean = sources
                noisy = noise + clean
            estimate = self.dmodel(noisy)
            # apply a loss function after each layer
            with torch.autograd.set_detect_anomaly(True):
                if self.args.loss == 'l1':
                    loss = F.l1_loss(clean, estimate)
                elif self.args.loss == 'l2':
                    loss = F.mse_loss(clean, estimate)
                elif self.args.loss == 'huber':
                    loss = F.smooth_l1_loss(clean, estimate)
                else:
                    raise ValueError(f"Invalid loss {self.args.loss}")
                # MultiResolution STFT loss
                if self.args.stft_loss:
                    sc_loss, mag_loss = self.mrstftloss(estimate.squeeze(1), clean.squeeze(1))
                    loss += sc_loss + mag_loss

                # optimize model in training mode
                if not cross_valid:
                    self.optimizer.zero_grad()
                    loss.backward()
                    self.optimizer.step()

            total_loss += loss.item()
            logprog.update(loss=format(total_loss / (i + 1), ".5f"))
            # Just in case, clear some memory
            del loss, estimate
        return distrib.average([total_loss / (i + 1)], i + 1)[0]
