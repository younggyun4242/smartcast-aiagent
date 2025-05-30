from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import OutputParserException
from openai import OpenAIError, APIError, RateLimitError, APIConnectionError, BadRequestError
import os
import logging
from typing import Optional, Dict, Any
import re
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
import backoff
import json
import time
import traceback
from binascii import unhexlify
from ..utils.logger import get_logger
from ..core.protocol import MessageFormat

# 로깅 설정
logger = get_logger('aiagent.services.parser')

class ParserError(Exception):
    """파서 관련 예외"""
    pass

class Parser:
    def __init__(self):
        # 환경 변수에서 OpenAI API 키 로드
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ParserError("OpenAI API 키가 설정되지 않았습니다.")
        
        try:
            self.llm = ChatOpenAI(
                model_name="gpt-4o", 
                temperature=0, 
                openai_api_key=self.api_key,
                request_timeout=30,  # 30초 타임아웃
                max_retries=3  # 최대 3번 재시도
            )
        except Exception as e:
            raise ParserError(f"LLM 초기화 실패: {str(e)}")

        # XML 태그 정의
        self.required_tags = {'TYPE', 'ORDER_ID', 'DATE', 'POS', 'MENU'}
        self.item_tags = {'NAME', 'COUNT', 'STATUS'}
        
        # 파서용 프롬프트 템플릿
        try:
            # 프롬프트 파일 읽기
            prompt_file = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'parser_prompt.txt')
            if not os.path.exists(prompt_file):
                raise ParserError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_file}")
                
            with open(prompt_file, 'r', encoding='utf-8') as f:
                template = f.read()
                
            self.prompt = PromptTemplate(
                input_variables=["receipt_text"],
                template=template
            )
            logger.debug(f"[Init] 프롬프트 파일 로드 완료: {prompt_file}")
            
        except Exception as e:
            raise ParserError(f"프롬프트 템플릿 초기화 실패: {str(e)}")

        # AI 병합용 프롬프트 템플릿 추가
        self.merge_prompt = PromptTemplate(
            input_variables=["current_xml", "receipt_data"],
            template="""
기존 XML 파싱 규칙과 새로운 영수증 데이터를 분석하여 개선된 TYPE 규칙을 생성해주세요.

기존 XML 규칙:
{current_xml}

새로운 영수증 데이터:
{receipt_data}

목표:
1. 새로운 영수증 형식을 올바르게 처리할 수 있도록 TYPE 규칙을 업데이트하세요.
2. 기존 구조를 최대한 유지하면서 필요한 부분만 수정하세요.
3. 새로운 패턴이나 예외 사항을 처리할 수 있도록 규칙을 확장하세요.

지시사항:
- 응답은 반드시 하나의 <TYPE> 블록만 포함해야 합니다.
- 완전한 TYPE XML 구조를 생성하세요 (ORDER_ID, DATE, POS, MENU 등 모든 필수 태그 포함).
- 설명이나 주석은 포함하지 마세요.
"""
        )

    def _extract_type(self, text: str) -> str:
        """
        텍스트에서 TYPE 부분만 추출
        """
        try:
            logger.debug(f"[Extract TYPE] 입력된 텍스트:\n{text}")
            
            # TYPE 태그 시작과 끝 찾기 (공백과 줄바꿈 포함)
            type_pattern = r"\s*<TYPE[^>]*>[\s\S]*?</TYPE>\s*"
            match = re.search(type_pattern, text, re.DOTALL)
            
            if not match:
                logger.error("[Extract TYPE] TYPE 태그를 찾을 수 없음")
                logger.error(f"[Extract TYPE] 검색 패턴: {type_pattern}")
                raise ParserError("TYPE 파싱 규칙을 찾을 수 없습니다")
                
            type_xml = match.group(0).strip()
            logger.debug(f"[Extract TYPE] 추출된 TYPE:\n{type_xml}")
            return type_xml
            
        except Exception as e:
            logger.error(f"[Extract TYPE] TYPE 추출 실패: {str(e)}")
            raise ParserError(f"TYPE 추출 실패: {str(e)}")

    def wrap_generated_type(self, type_xml: str) -> str:
        """
        생성된 TYPE XML을 고정 구조로 감싸기
        """
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<PARSER
    name="deepkds"
    id="orderParser"
    type="a"
    cut="n"
    remove="a!0|a1|a0|B0|E0|!F|!@|!|[CUT]|대기번호확인"
    replace="[BIG]=[NOR]|[VER]=[NOR]|[BLD]=[NOR]|[BAR]=[NOR]영수증번호 : |[NOR]=\\n">

  <NORMAL contain="추가-|신규-|취소-|환불-" count="1">
    {type_xml.strip()}
  </NORMAL>
</PARSER>'''

    def _validate_xml_structure(self, xml_str: str) -> None:
        """
        파싱 결과 XML 구조 검증 (RECEIPT 루트 태그)
        """
        try:
            # XML 파싱
            root = ET.fromstring(xml_str)
            
            # 루트 태그 확인 (파싱 결과는 RECEIPT가 루트)
            if root.tag != "RECEIPT":
                raise ParserError("루트 태그가 RECEIPT가 아닙니다")
            
            # 필수 태그 확인
            found_tags = {child.tag for child in root}
            missing_tags = self.required_tags - found_tags
            if missing_tags:
                raise ParserError(f"필수 태그가 누락됨: {missing_tags}")
            
            # MENU 내부의 ITEM 태그 확인
            menu = root.find("MENU")
            if menu is None:
                raise ParserError("MENU 태그를 찾을 수 없습니다")
            
            items = menu.findall("ITEM")
            if not items:
                raise ParserError("MENU 태그 내에 ITEM이 없습니다")
            
            # 각 ITEM의 필수 태그 확인
            for idx, item in enumerate(items, 1):
                item_found_tags = {child.tag for child in item}
                missing_item_tags = self.item_tags - item_found_tags
                if missing_item_tags:
                    details = []
                    for tag in missing_item_tags:
                        if tag == "NAME":
                            details.append("NAME (메뉴 이름)")
                        elif tag == "COUNT":
                            details.append("COUNT (수량)")
                        elif tag == "STATUS":
                            details.append("STATUS (상태)")
                    error_msg = f"{idx}번째 ITEM에서 다음 태그가 누락됨: {', '.join(details)}"
                    raise ParserError(error_msg)
                
            # TYPE, DATE 값 공백 체크
            for tag in ["TYPE", "DATE"]:
                elem = root.find(tag)
                if elem is None or not (elem.text and elem.text.strip()):
                    raise ParserError(f"{tag} 태그의 값이 비어있습니다")

            # ITEM 내부 NAME, COUNT, STATUS 값 공백 체크
            for idx, item in enumerate(items, 1):
                for tag in self.item_tags:
                    elem = item.find(tag)
                    if elem is None or not (elem.text and elem.text.strip()):
                        raise ParserError(f"{idx}번째 ITEM의 {tag} 태그 값이 비어있습니다")
                
        except ParseError as e:
            raise ParserError(f"잘못된 XML 형식: {str(e)}")
        except ParserError:
            raise
        except Exception as e:
            raise ParserError(f"XML 구조 검증 실패: {str(e)}")

    def _clean_xml(self, xml_str: str) -> str:
        """
        XML 문자열 정제
        - 불필요한 공백 제거
        - 빈 줄 제거
        - 들여쓰기 정리
        """
        try:
            # XML 파싱
            root = ET.fromstring(xml_str)
            
            # XML 문자열로 변환 (들여쓰기 포함)
            ET.indent(root, space="  ")
            clean_xml = ET.tostring(root, encoding='unicode')
            
            return clean_xml
            
        except Exception as e:
            raise ParserError(f"XML 정제 실패: {str(e)}")

    @backoff.on_exception(
        backoff.expo,
        (RateLimitError, APIConnectionError),
        max_tries=5,
        max_time=30
    )
    def _call_llm(self, prompt_text: str) -> str:
        """LLM 호출 with 재시도 로직"""
        try:
            response = self.llm.predict(prompt_text)
            logger.debug(f"[LLM Response] GPT 응답:\n{response}")
            return response
        except RateLimitError:
            logger.warning("API 속도 제한에 걸림, 재시도 중...")
            raise
        except APIConnectionError:
            logger.warning("API 연결 오류, 재시도 중...")
            raise
        except APIError as e:
            logger.error(f"OpenAI API 오류: {str(e)}")
            raise ParserError(f"OpenAI API 오류: {str(e)}")
        except BadRequestError as e:
            logger.error(f"잘못된 API 요청: {str(e)}")
            raise ParserError(f"잘못된 API 요청: {str(e)}")
        except OpenAIError as e:
            logger.error(f"OpenAI 관련 오류: {str(e)}")
            raise ParserError(f"OpenAI 오류: {str(e)}")
        except OutputParserException as e:
            logger.error(f"LangChain 출력 파싱 오류: {str(e)}")
            raise ParserError(f"출력 파싱 오류: {str(e)}")
        except Exception as e:
            logger.error(f"예상치 못한 LLM 오류: {str(e)}")
            raise ParserError(f"LLM 호출 실패: {str(e)}")

    def _decode_raw_data(self, raw_data: str) -> str:
        """
        hex 형식의 raw_data를 텍스트로 변환
        
        Args:
            raw_data: hex 형식의 문자열
            
        Returns:
            변환된 텍스트
            
        Raises:
            ParserError: 변환 실패 시
        """
        try:
            # hex 문자열을 바이트로 변환
            raw = unhexlify(raw_data)
            
            # euc-kr로 디코딩 시도
            try:
                text = raw.decode("euc-kr", errors="ignore")
            except:
                # 실패하면 cp949로 시도
                try:
                    text = raw.decode("cp949", errors="ignore")
                except:
                    # 모두 실패하면 기본 디코딩
                    text = raw.decode(errors="ignore")
            
            # 영수증 프린터 특성을 고려한 텍스트 정제
            # 1. 일반적인 줄바꿈 처리
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            
            # 2. ESC/POS 명령어 패턴 제거 (예: \x1b[숫자])
            text = re.sub(r'\x1b\[[0-9;]*[mGKHfhlABCDJ]', '', text)
            text = re.sub(r'\x1b[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/`~]', '', text)
            
            # 3. 기타 컨트롤 문자 제거 (줄바꿈, 탭은 보존)
            text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
            
            # 4. 줄바꿈이 제대로 되지 않은 경우 강제 줄바꿈 추가
            # 영수증에서 일반적인 패턴들을 기준으로 줄바꿈 추가
            if '\n' not in text or text.count('\n') < 3:  # 줄바꿈이 거의 없는 경우
                logger.debug("[Raw Data Decode] 줄바꿈이 부족하여 패턴 기반 줄바꿈 추가")
                
                # 영수증 프린터의 구분자 패턴들
                patterns = [
                    r'(!)([!])',  # ! 연속 패턴
                    r'(=)([=]{5,})',  # = 연속 패턴
                    r'(-)([-]{5,})',  # - 연속 패턴
                    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',  # 날짜 시간
                    r'(POS:\d+)',  # POS 번호
                    r'(\[주문번호\][^!]+)',  # 주문번호
                    r'(\[주문시간\][^!]+)',  # 주문시간
                    r'(\[주방메모\])',  # 주방메모
                    r'(\[테이블\][^!]+)',  # 테이블
                ]
                
                for pattern in patterns:
                    text = re.sub(pattern, r'\1\n\2', text)
                
                # 메뉴 구분선 처리
                text = re.sub(r'(구분)([-]{10,})', r'\1\n\2\n', text)
                text = re.sub(r'(메\s*뉴\s*명[^-]*)([-]{10,})', r'\1\n\2\n', text)
                
                # 연속된 줄바꿈 정리
                text = re.sub(r'\n\s*\n', '\n', text)
            
            # 5. 각 줄의 앞뒤 공백 제거 후 재조합
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)
            
            logger.debug(f"[Raw Data Decode] 변환된 텍스트 (줄 수: {len(lines)}):\n{text}")
            return text
            
        except Exception as e:
            logger.error(f"[Raw Data Decode] hex 데이터 변환 실패: {str(e)}")
            raise ParserError(f"hex 데이터 변환 실패: {str(e)}")

    def _extract_value(self, lines: list, rule_elem: ET.Element) -> str:
        """
        파싱 규칙에 따라 값 추출 - EscposParser 스타일
        """
        if rule_elem is None:
            return ""
            
        try:
            # 규칙 속성 추출
            contain = rule_elem.get('contain', '')
            begin = rule_elem.get('begin', '')
            min_len = rule_elem.get('min', '')
            max_len = rule_elem.get('max', '')
            left_align = rule_elem.get('left', '')
            right_align = rule_elem.get('right', '')
            regex = rule_elem.get('regex', '')
            default = rule_elem.get('default', '')
            
            # 정규식 우선 처리
            if regex:
                full_text = '\n'.join(line.get('text', '') if isinstance(line, dict) else str(line) for line in lines)
                match = re.search(regex, full_text)
                if match:
                    value = match.group(1)
                    return self._format_value(value, min_len, max_len, left_align, right_align)
                return default
            
            # 일반 토큰 추출
            for line in lines:
                text = line.get('text', '').strip() if isinstance(line, dict) else str(line).strip()
                
                if contain and contain in text:
                    tmp = text.split(contain, 1)[1]
                    if begin and begin in tmp:
                        tmp = tmp.split(begin, 1)[1]
                    
                    tokens = tmp.strip().split()
                    if tokens:
                        value = tokens[0]
                        return self._format_value(value, min_len, max_len, left_align, right_align)
            
            return default
            
        except Exception as e:
            logger.error(f"[Extract Value] 값 추출 실패: {str(e)}")
            return ""

    def _format_value(self, value: str, min_len: str, max_len: str, left_align: str, right_align: str) -> str:
        """값 포맷팅 (길이 및 정렬)"""
        try:
            # 최대 길이 처리
            if max_len and max_len.isdigit():
                max_len_val = int(max_len)
                if len(value) > max_len_val:
                    value = value[:max_len_val]
            
            # 최소 길이 처리
            if min_len and min_len.isdigit():
                min_len_val = int(min_len)
                if len(value) < min_len_val:
                    value = value.ljust(min_len_val)
            
            # 좌우 정렬
            if left_align and left_align.isdigit():
                value = value.ljust(int(left_align))
            if right_align and right_align.isdigit():
                value = value.rjust(int(right_align))
            
            return value.strip()
            
        except Exception as e:
            logger.error(f"[Format Value] 값 포맷팅 실패: {str(e)}")
            return value

    def _extract_menu_items(self, lines: list, menu_rule: ET.Element) -> list:
        """
        메뉴 항목 추출 - EscposParser 스타일
        """
        items = []
        if menu_rule is None:
            logger.error("[Extract Menu] menu_rule이 None입니다")
            return items
            
        try:
            # 필드 정의 수집
            fields = []
            for field_elem in menu_rule:
                tag = field_elem.tag.lower()
                if tag not in ('name', 'count', 'price', 'amount', 'status'):
                    continue
                    
                fields.append({
                    'key': tag,
                    'take': field_elem.get('take'),
                    'idx_begin': field_elem.get('idx_begin'),
                    'idx_end': field_elem.get('idx_end'),
                    'regex': field_elem.get('regex'),
                    'default': field_elem.get('default', '')
                })
            
            logger.debug(f"[Extract Menu] 수집된 필드 정의:\n{json.dumps(fields, ensure_ascii=False, indent=2)}")

            # 메뉴 영역 찾기
            begin_marker = menu_rule.get('begin', '')
            end_marker = menu_rule.get('end', '')
            skip_marker = menu_rule.get('skip', '')
            
            logger.debug(f"[Extract Menu] 메뉴 영역 마커:\nbegin: {begin_marker}\nend: {end_marker}\nskip: {skip_marker}")
            
            # 시작/끝 인덱스 찾기
            start_idx = 0
            end_idx = len(lines)
            
            # 전체 라인 로깅
            logger.debug("[Extract Menu] 전체 라인:")
            for i, line in enumerate(lines):
                logger.debug(f"[{i}] {line}")
            
            if begin_marker:
                for i, line in enumerate(lines):
                    text = line.get('text', '') if isinstance(line, dict) else str(line)
                    if begin_marker in text:
                        # 시작 마커가 있는 줄부터 파싱 시작 (마커 다음 줄이 아닌)
                        start_idx = i
                        logger.debug(f"[Extract Menu] 시작 마커 발견 - 인덱스: {i}, 라인: {text}")
                        break
                        
            if end_marker:
                for i in range(start_idx, len(lines)):
                    text = lines[i].get('text', '') if isinstance(lines[i], dict) else str(lines[i])
                    if end_marker in text:
                        end_idx = i
                        logger.debug(f"[Extract Menu] 종료 마커 발견 - 인덱스: {i}, 라인: {text}")
                        break
            
            logger.debug(f"[Extract Menu] 메뉴 영역 인덱스: {start_idx} ~ {end_idx}")
            
            # 메뉴 영역 라인 로깅
            logger.debug("[Extract Menu] 메뉴 영역 라인:")
            for i in range(start_idx, end_idx):
                logger.debug(f"[{i}] {lines[i]}")
            
            # 메뉴 영역 파싱
            for line in lines[start_idx:end_idx]:
                text = line.get('text', '').strip() if isinstance(line, dict) else str(line).strip()
                
                # 같은 줄에 시작과 끝 마커가 모두 있는 경우 해당 구간만 추출
                if begin_marker and end_marker and begin_marker in text and end_marker in text:
                    logger.debug(f"[Extract Menu] 같은 줄에 시작/끝 마커 발견: {text}")
                    begin_pos = text.find(begin_marker) + len(begin_marker)
                    end_pos = text.find(end_marker)
                    if begin_pos < end_pos:
                        text = text[begin_pos:end_pos].strip()
                        logger.debug(f"[Extract Menu] 추출된 메뉴 구간: {text}")
                
                # 빈 줄이나 건너뛸 항목 제외
                if not text:
                    logger.debug(f"[Extract Menu] 빈 라인 무시: {line}")
                    continue
                if skip_marker and skip_marker in text:
                    logger.debug(f"[Extract Menu] 건너뛸 라인 발견: {line}")
                    continue
                    
                parts = text.split()
                if not parts:
                    logger.debug(f"[Extract Menu] 분할 후 빈 라인: {line}")
                    continue
                    
                logger.debug(f"[Extract Menu] 라인 분석 중: {text}")
                logger.debug(f"[Extract Menu] 분할된 부분: {parts}")
                
                item = {}
                total_parts = len(parts)
                
                for field in fields:
                    key = field['key']
                    
                    # 1. 정규식 처리
                    if field['regex']:
                        match = re.search(field['regex'], text)
                        item[key] = match.group(1) if match else field['default']
                        logger.debug(f"[Extract Menu] 정규식 처리 결과 - {key}: {item[key]}")
                        continue
                    
                    # 2. "all_before" 처리
                    if field['take'] == 'all_before':
                        other_indexes = []
                        for other in fields:
                            if other['idx_begin'] and other['key'] != key:
                                try:
                                    idx = int(other['idx_begin'])
                                    other_indexes.append(idx if idx >= 0 else total_parts + idx)
                                except:
                                    pass
                        cut_idx = min(other_indexes) if other_indexes else total_parts - 1
                        item[key] = ' '.join(parts[:cut_idx]) if key == 'name' else field['default']
                        logger.debug(f"[Extract Menu] all_before 처리 결과 - {key}: {item[key]}")
                        continue
                    
                    # 3. 인덱스 기반 처리
                    idx_begin = field['idx_begin']
                    idx_end = field['idx_end']
                    
                    if idx_begin and idx_begin.lstrip('-').isdigit():
                        begin = int(idx_begin)
                        if begin < 0:
                            begin = total_parts + begin
                            
                        end = begin + 1
                        if idx_end and idx_end.lstrip('-').isdigit():
                            end = int(idx_end)
                            if end < 0:
                                end = total_parts + end
                        
                        if 0 <= begin < total_parts:
                            if key == 'name':
                                item[key] = ' '.join(parts[begin:end])
                            else:
                                item[key] = parts[begin] if begin < total_parts else field['default']
                        else:
                            item[key] = field['default']
                        logger.debug(f"[Extract Menu] 인덱스 처리 결과 - {key}: {item[key]} (begin: {begin}, end: {end})")
                    else:
                        item[key] = field['default']
                        logger.debug(f"[Extract Menu] 기본값 사용 - {key}: {item[key]}")
                
                # 첫 번째 필드가 비어있으면 제외
                first_key = fields[0]['key'] if fields else None
                if first_key and not item.get(first_key, '').strip():
                    logger.debug(f"[Extract Menu] 첫 번째 필드가 비어있어 제외: {item}")
                    continue
                    
                # 모든 필드가 비어있거나 기본값이면 제외
                if any(v.strip() for v in item.values()):
                    items.append(item)
                    logger.debug(f"[Extract Menu] 항목 추가됨: {item}")
                else:
                    logger.debug(f"[Extract Menu] 모든 필드가 비어있어 제외: {item}")
            
            logger.debug(f"[Extract Menu] 추출된 총 메뉴 항목 수: {len(items)}")
            return items
            
        except Exception as e:
            logger.error(f"[Extract Menu] 메뉴 추출 실패: {str(e)}")
            logger.error(f"[Extract Menu] 스택 트레이스:\n{traceback.format_exc()}")
            return items

    def generate_rule(self, receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        """새로운 파싱 규칙 생성 - TYPE만 생성하고 고정 구조로 감싸기"""
        try:
            logger.debug("[Generate Rule] 새로운 파싱 규칙 생성 시작")
            logger.debug(f"[Generate Rule] 입력 데이터:\n{json.dumps(receipt_data, ensure_ascii=False, indent=2)}")
            
            # protocol.py의 extract_receipt_raw_data 함수 사용 (문자열/객체 형태 모두 지원)
            try:
                raw_data = MessageFormat.extract_receipt_raw_data(receipt_data)
                logger.debug(f"[Generate Rule] 추출된 raw_data(hex):\n{raw_data}")
            except ValueError as e:
                logger.error(f"[Generate Rule] raw_data 추출 실패: {str(e)}")
                logger.error(f"[Generate Rule] receipt_data 내용: {receipt_data.get('receipt_data', {})}")
                raise ParserError(f"raw_data 추출 실패: {str(e)}")
            
            receipt_text = self._decode_raw_data(raw_data)
            logger.debug(f"[Generate Rule] 변환된 영수증 텍스트:\n{receipt_text}")
            
            # 프롬프트 생성 및 로깅 (TYPE만 생성하도록 변경된 프롬프트 사용)
            prompt = self.prompt.format(receipt_text=receipt_text)
            logger.debug(f"[Generate Rule] GPT 프롬프트:\n{prompt}")
            
            # TYPE 규칙 생성
            llm_response = self._call_llm(prompt)
            logger.debug(f"[Generate Rule] GPT 응답 원본:\n{llm_response}")
            
            # TYPE 추출
            type_xml = self._extract_type(llm_response)
            logger.debug(f"[Generate Rule] 추출된 TYPE:\n{type_xml}")
            
            # TYPE 구조 검증
            self._validate_type_structure(type_xml)
            logger.debug("[Generate Rule] TYPE 구조 검증 완료")
            
            # TYPE을 고정 구조로 감싸기
            complete_xml = self.wrap_generated_type(type_xml)
            logger.debug(f"[Generate Rule] 완성된 XML 규칙:\n{complete_xml}")
            
            # 생성된 규칙을 실제 데이터에 적용해보기 (검증)
            try:
                logger.debug("[Generate Rule] 생성된 규칙 적용 테스트 시작")
                test_result = self.apply_rule(receipt_text, complete_xml)
                logger.debug(f"[Generate Rule] 규칙 적용 결과:\n{test_result}")
                
                # 파싱 결과 검증
                self._validate_xml_structure(test_result)
                logger.debug("[Generate Rule] 규칙 적용 결과 검증 완료")
                
            except Exception as e:
                logger.error(f"[Generate Rule] 규칙 적용 테스트 실패: {str(e)}")
                raise ParserError(f"생성된 파싱 규칙 검증 실패: {str(e)}")
            
            # 버전 생성 (client_id_001.xml 형식)
            version = f"{receipt_data['client_id']}_001.xml"
            
            return {
                "status": "ok",
                "rule_xml": complete_xml,
                "version": version
            }
            
        except Exception as e:
            logger.error(f"[Generate Rule] 규칙 생성 실패: {str(e)}")
            raise ParserError(f"파싱 규칙 생성 실패: {str(e)}")

    def apply_rule(self, receipt_text: str, parser_xml: str) -> str:
        """
        파싱 규칙을 적용하여 영수증 데이터를 XML로 변환

        Args:
            receipt_text: 영수증 텍스트 데이터 (hex 데이터가 변환된 텍스트)
            parser_xml: 파싱 규칙이 정의된 XML

        Returns:
            파싱된 영수증 XML 문자열
        """
        try:
            logger.debug("[Apply Rule] 파싱 규칙 적용 시작")

            # 파싱 규칙 XML 파싱
            parser_root = ET.fromstring(parser_xml)
            normal_block = parser_root.find("NORMAL")
            if normal_block is None:
                raise ParserError("NORMAL 블록을 찾을 수 없습니다.")

            # 텍스트를 줄 단위로 분리
            lines = receipt_text.strip().splitlines()

            # TYPE 선택
            chosen_type = None
            for type_elem in normal_block.findall("TYPE"):
                contain_str = type_elem.get("contain", "")
                for pattern in contain_str.split("|"):
                    if pattern and any(pattern in line for line in lines):
                        chosen_type = type_elem
                        break
                if chosen_type:
                    break

            if not chosen_type:
                raise ParserError("매칭되는 영수증 타입을 찾을 수 없습니다.")

            # 결과 XML 생성
            receipt_root = ET.Element("RECEIPT")

            # TYPE 태그
            type_tag = ET.SubElement(receipt_root, "TYPE")
            type_tag.text = chosen_type.get("name", "")

            # 기본 필드 추출
            for tag in self.required_tags:
                if tag in {"TYPE", "MENU"}:
                    continue
                node = chosen_type.find(tag)
                if node is not None:
                    value = self._extract_value(lines, node)
                    if value:
                        elem = ET.SubElement(receipt_root, tag)
                        elem.text = value

            # MENU 항목 처리
            menu = ET.SubElement(receipt_root, "MENU")
            menu_items = self._extract_menu_items(lines, chosen_type.find("MENU"))

            if not menu_items:
                raise ParserError("MENU 항목이 없습니다. 파싱 실패")

            for item in menu_items:
                item_elem = ET.SubElement(menu, "ITEM")
                for tag in self.item_tags:
                    tag_elem = ET.SubElement(item_elem, tag)
                    tag_elem.text = str(item.get(tag.lower(), ""))

            # XML 문자열로 반환
            return ET.tostring(receipt_root, encoding='unicode')

        except Exception as e:
            logger.error(f"[Apply Rule] 규칙 적용 실패: {str(e)}")
            logger.error(f"[Apply Rule] 스택 트레이스:\n{traceback.format_exc()}")
            raise ParserError(f"파싱 규칙 적용 실패: {str(e)}")

    def _validate_type_structure(self, type_xml: str) -> None:
        """
        생성된 TYPE XML 구조 검증
        """
        try:
            # TYPE XML 파싱
            type_root = ET.fromstring(type_xml)
            
            # 루트 태그 확인
            if type_root.tag != "TYPE":
                raise ParserError("루트 태그가 TYPE이 아닙니다")
            
            # TYPE 필수 속성 확인
            if not type_root.get("name"):
                raise ParserError("TYPE 태그에 name 속성이 없습니다")
            if not type_root.get("contain"):
                raise ParserError("TYPE 태그에 contain 속성이 없습니다")
            
            # 필수 하위 태그 확인
            required_child_tags = {'ORDER_ID', 'DATE', 'POS', 'MENU'}
            found_child_tags = {child.tag for child in type_root}
            missing_child_tags = required_child_tags - found_child_tags
            if missing_child_tags:
                raise ParserError(f"TYPE 내 필수 태그가 누락됨: {missing_child_tags}")
            
            # MENU 태그 내부 구조 확인
            menu = type_root.find("MENU")
            if menu is None:
                raise ParserError("MENU 태그를 찾을 수 없습니다")
            
            # MENU 내 필수 하위 태그 확인
            menu_child_tags = {child.tag for child in menu}
            required_menu_tags = {'NAME', 'COUNT', 'STATUS'}
            missing_menu_tags = required_menu_tags - menu_child_tags
            if missing_menu_tags:
                raise ParserError(f"MENU 내 필수 태그가 누락됨: {missing_menu_tags}")
                
        except ParseError as e:
            raise ParserError(f"잘못된 TYPE XML 형식: {str(e)}")
        except ParserError:
            raise
        except Exception as e:
            raise ParserError(f"TYPE XML 구조 검증 실패: {str(e)}")

    def merge_rule(self, current_xml: str, current_version: str, receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        """기존 XML과 새로운 데이터 병합 - GPT를 통해 적절한 순서로 TYPE 배치"""
        try:
            logger.debug("[Merge Rule] XML 병합 시작")
            logger.debug(f"[Merge Rule] 현재 XML:\n{current_xml}")
            logger.debug(f"[Merge Rule] 현재 버전: {current_version}")
            
            # protocol.py의 extract_receipt_raw_data 함수 사용 (문자열/객체 형태 모두 지원)
            try:
                raw_data = MessageFormat.extract_receipt_raw_data(receipt_data)
                logger.debug(f"[Merge Rule] 추출된 raw_data(hex):\n{raw_data}")
            except ValueError as e:
                logger.error(f"[Merge Rule] raw_data 추출 실패: {str(e)}")
                raise ParserError(f"raw_data 추출 실패: {str(e)}")
            
            receipt_text = self._decode_raw_data(raw_data)
            logger.debug(f"[Merge Rule] 변환된 영수증 텍스트:\n{receipt_text}")
            
            # 기존 XML에서 TYPE 규칙들 추출
            existing_types = self._extract_existing_types(current_xml)
            logger.debug(f"[Merge Rule] 기존 TYPE 개수: {len(existing_types)}")
            
            # 병합 프롬프트 생성 (여러 TYPE을 적절한 순서로 배치)
            merge_prompt = self._create_merge_prompt(existing_types, receipt_text)
            logger.debug(f"[Merge Rule] 병합 프롬프트:\n{merge_prompt}")
            
            # LLM 호출하여 병합된 TYPE들 생성
            llm_response = self._call_llm(merge_prompt)
            logger.debug(f"[Merge Rule] GPT 응답 원본:\n{llm_response}")
            
            # 모든 TYPE들 추출 및 검증
            merged_types = self._extract_multiple_types(llm_response)
            logger.debug(f"[Merge Rule] 추출된 TYPE 개수: {len(merged_types)}")
            
            # 각 TYPE 구조 검증
            for i, type_xml in enumerate(merged_types):
                self._validate_type_structure(type_xml)
                logger.debug(f"[Merge Rule] TYPE {i+1} 구조 검증 완료")
            
            # 모든 TYPE을 고정 구조로 감싸기
            merged_xml = self._wrap_multiple_types(merged_types)
            logger.debug(f"[Merge Rule] 병합된 XML:\n{merged_xml}")
            
            # 병합된 규칙을 실제 데이터에 적용해보기 (검증)
            try:
                logger.debug("[Merge Rule] 병합된 규칙 적용 테스트 시작")
                test_result = self.apply_rule(receipt_text, merged_xml)
                logger.debug(f"[Merge Rule] 규칙 적용 결과:\n{test_result}")
                
                # 파싱 결과 검증
                self._validate_xml_structure(test_result)
                logger.debug("[Merge Rule] 병합된 규칙 적용 결과 검증 완료")
                
            except Exception as e:
                logger.error(f"[Merge Rule] 병합된 규칙 적용 테스트 실패: {str(e)}")
                raise ParserError(f"병합된 파싱 규칙 검증 실패: {str(e)}")
            
            # 새 버전 생성 (+1)
            new_version = self._increment_version(current_version)
            
            return {
                "status": "ok",
                "merged_rule_xml": merged_xml,
                "version": new_version,
                "changes": [f"새로운 영수증 패턴 추가 (총 {len(merged_types)}개 타입)"]
            }
            
        except Exception as e:
            logger.error(f"[Merge Rule] 병합 실패: {str(e)}")
            raise ParserError(f"파싱 규칙 병합 실패: {str(e)}")

    def _extract_existing_types(self, xml_str: str) -> list:
        """기존 XML에서 TYPE들 추출"""
        try:
            # XML 파싱
            root = ET.fromstring(xml_str)
            normal_block = root.find("NORMAL")
            if normal_block is None:
                logger.warning("[Extract Existing Types] NORMAL 블록을 찾을 수 없음")
                return []
            
            # 모든 TYPE 요소들 추출
            types = []
            for type_elem in normal_block.findall("TYPE"):
                # TYPE 요소를 문자열로 변환
                type_str = ET.tostring(type_elem, encoding='unicode')
                types.append(type_str)
                logger.debug(f"[Extract Existing Types] TYPE 추출: {type_elem.get('name', 'Unknown')}")
            
            logger.debug(f"[Extract Existing Types] 총 {len(types)}개 TYPE 추출됨")
            return types
            
        except Exception as e:
            logger.error(f"[Extract Existing Types] TYPE 추출 실패: {str(e)}")
            return []

    def _create_merge_prompt(self, existing_types: list, new_receipt: str) -> str:
        """여러 TYPE을 적절한 순서로 배치하는 프롬프트 생성"""
        
        # 기존 TYPE들을 문자열로 조합
        existing_types_str = "\n\n".join(existing_types) if existing_types else "기존 TYPE 없음"
        
        prompt = f"""
기존 파싱 규칙들과 새로운 영수증 데이터를 분석하여, 모든 TYPE들을 적절한 순서로 배치한 완전한 파싱 규칙을 생성해주세요.

기존 TYPE 규칙들:
{existing_types_str}

새로운 영수증 데이터:
{new_receipt}

작업 지시사항:
1. 새로운 영수증 데이터에 맞는 새로운 TYPE을 생성하세요.
2. 기존 TYPE들은 최대한 유지하되, 필요시 개선하세요.
3. 모든 TYPE들을 적절한 우선순위 순서로 배치하세요 (더 구체적인 패턴이 앞에 오도록).
4. 각 TYPE은 고유한 name과 contain 속성을 가져야 합니다.

응답 형식:
- 여러 개의 <TYPE>...</TYPE> 블록을 순서대로 나열해주세요.
- 각 TYPE은 완전한 구조(ORDER_ID, DATE, POS, MENU 포함)를 가져야 합니다.
- 설명이나 주석은 포함하지 마세요.
- TYPE 태그 외의 다른 태그는 포함하지 마세요.

예시:
<TYPE name="타입1" contain="패턴1">
  <ORDER_ID ... />
  <DATE ... />
  <POS ... />
  <MENU ...>
    <NAME ... />
    <COUNT ... />
    <STATUS ... />
  </MENU>
</TYPE>

<TYPE name="타입2" contain="패턴2">
  ...
</TYPE>
"""
        return prompt

    def _extract_multiple_types(self, response: str) -> list:
        """GPT 응답에서 여러 TYPE들 추출"""
        try:
            logger.debug(f"[Extract Multiple Types] GPT 응답 분석 시작")
            
            # TYPE 태그들을 모두 찾기
            type_pattern = r'<TYPE[^>]*>[\s\S]*?</TYPE>'
            matches = re.findall(type_pattern, response, re.DOTALL)
            
            types = []
            for i, match in enumerate(matches):
                # 각 TYPE의 공백 정리
                type_xml = match.strip()
                logger.debug(f"[Extract Multiple Types] TYPE {i+1} 추출: {type_xml[:100]}...")
                types.append(type_xml)
            
            logger.debug(f"[Extract Multiple Types] 총 {len(types)}개 TYPE 추출됨")
            
            if not types:
                logger.error("[Extract Multiple Types] TYPE 태그를 찾을 수 없음")
                raise ParserError("GPT 응답에서 TYPE 태그를 찾을 수 없습니다")
            
            return types
            
        except Exception as e:
            logger.error(f"[Extract Multiple Types] TYPE 추출 실패: {str(e)}")
            raise ParserError(f"Multiple TYPE 추출 실패: {str(e)}")

    def _wrap_multiple_types(self, types: list) -> str:
        """여러 TYPE을 고정 구조로 감싸기"""
        try:
            # 모든 TYPE들을 NORMAL 블록 안에 배치
            types_content = "\n    ".join(types)
            
            wrapped_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<PARSER
    name="deepkds"
    id="orderParser"
    type="a"
    cut="n"
    remove="a!0|a1|a0|B0|E0|!F|!@|!|[CUT]|대기번호확인"
    replace="[BIG]=[NOR]|[VER]=[NOR]|[BLD]=[NOR]|[BAR]=[NOR]영수증번호 : |[NOR]=\\n">

  <NORMAL contain="추가-|신규-|취소-|환불-" count="1">
    {types_content}
  </NORMAL>
</PARSER>'''

            logger.debug(f"[Wrap Multiple Types] {len(types)}개 TYPE을 PARSER 구조로 감쌈")
            return wrapped_xml
            
        except Exception as e:
            logger.error(f"[Wrap Multiple Types] XML 감싸기 실패: {str(e)}")
            raise ParserError(f"Multiple TYPE XML 감싸기 실패: {str(e)}")

    def _increment_version(self, current_version: str) -> str:
        """버전 번호 +1"""
        try:
            # "PXMXBI_001.xml" 형식에서 숫자 부분 추출
            if "_" in current_version and current_version.endswith(".xml"):
                parts = current_version.split("_")
                if len(parts) >= 2:
                    client_id = parts[0]
                    version_part = parts[1].split(".")[0]  # "001" 부분
                    
                    try:
                        version_num = int(version_part)
                        new_version = f"{client_id}_{version_num + 1:03d}.xml"
                        logger.debug(f"[Increment Version] {current_version} → {new_version}")
                        return new_version
                    except ValueError:
                        pass
            
            # 파싱 실패시 기본 처리
            logger.warning(f"[Increment Version] 버전 파싱 실패, 기본 처리: {current_version}")
            if current_version.endswith(".xml"):
                base = current_version[:-4]
                return f"{base}_002.xml"
            else:
                return f"{current_version}_002.xml"
                
        except Exception as e:
            logger.error(f"[Increment Version] 버전 증가 실패: {str(e)}")
            return f"{current_version}_new.xml"

# 싱글톤 인스턴스 생성
try:
    parser = Parser()
except Exception as e:
    logger.error(f"파서 초기화 실패: {str(e)}")
    parser = None
